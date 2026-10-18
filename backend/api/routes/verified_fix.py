from __future__ import annotations

import ast
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.routes.correction import (
    _build_updated_file,
    _resolve_correction_repository,
    _resolve_python_file,
)
from backend.api.schemas import CorrectionRequest
from backend.services.ai_correction import AICorrectionService, CorrectionInput
from backend.services.code_correction import CodeCorrectionService
from backend.services.ai_correction_provider import FallbackCorrectionProvider
from backend.services.ai_explainer import AIExplainerService
from backend.services.ai_verification import AIVerificationService
from backend.services.patch_registry import patch_registry
from backend.services.sandbox_verification import SandboxVerificationService
from backend.services.security_rescan import infer_rule_id

router = APIRouter(prefix="/correction", tags=["verified-correction"])

code_correction_service = CodeCorrectionService()
verifier = SandboxVerificationService()
ai_verifier = AIVerificationService()
ai_explainer = AIExplainerService()


class VerifiedFixRequest(CorrectionRequest):
    max_attempts: int = Field(default=3, ge=1, le=5)
    rule_id: str | None = None  # e.g. SQL_INJECTION; inferred from `finding` if empty
    force_fix: bool = False  # True => try a fix even if the explainer says false positive


class Verification(BaseModel):
    status: str
    message: str
    verification_level: str = "none"
    sandbox: str = "none"
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    regressions: list[str] = Field(default_factory=list)
    security: dict | None = None


class Attempt(BaseModel):
    attempt: int
    status: str
    message: str


class VerifiedFixResponse(BaseModel):
    status: str  # "verified" | "unverified"
    message: str
    proposal_id: str | None = None
    file_path: str
    function_name: str
    corrected_code: str | None = None  # only when verified
    explanation: str | None = None
    patch: str | None = None
    verification: Verification | None = None
    attempts: list[Attempt] = Field(default_factory=list)
    risk_explanation: dict | None = None  # explainer agent output
    ai_review: dict | None = None  # LLM second opinion
    requires_human_review: bool = True


class ExplainResponse(BaseModel):
    file_path: str
    function_name: str
    explanation: dict | None = None  # None => no AI provider available
    ai_available: bool = False


def _explain(req: CorrectionRequest, root: Path, rel: str) -> dict | None:
    """Explainer agent. Never blocks the pipeline: returns None on any problem."""
    try:
        target = _resolve_python_file(root, rel)
        code = code_correction_service.extract_function(target, req.function_name)
    except (HTTPException, FileNotFoundError, ValueError, OSError):
        return None
    result = ai_explainer.explain(
        file_path=rel, function_name=req.function_name, code=code,
        severity=req.severity, finding=req.finding, static_explanation=req.explanation)
    return result.to_dict() if result else None


@router.post("/explain", response_model=ExplainResponse)
def explain_risk(request: CorrectionRequest) -> ExplainResponse:
    """Explainer agent only: why is this function risky? Does not modify anything."""
    root, clone_workspace = _resolve_correction_repository(request.repository_path, request.github_url)
    rel = Path(request.file_path).as_posix()
    try:
        data = _explain(request, root, rel)
    finally:
        if clone_workspace is not None:
            shutil.rmtree(clone_workspace, ignore_errors=True)
    return ExplainResponse(file_path=rel, function_name=request.function_name,
                           explanation=data, ai_available=data is not None)


def _signature(node) -> tuple:
    a = node.args
    return ([x.arg for x in a.posonlyargs], [x.arg for x in a.args],
            a.vararg.arg if a.vararg else None,
            [x.arg for x in a.kwonlyargs], a.kwarg.arg if a.kwarg else None)


def _find(source: str, name: str):
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _is_unchanged(original: str, corrected: str) -> bool:
    """True when the 'fix' is the same code (ignoring comments/whitespace)."""
    try:
        return ast.dump(ast.parse(original.strip())) == ast.dump(ast.parse(corrected.strip()))
    except SyntaxError:
        return original.strip() == corrected.strip()


def _signature_problem(original: str, corrected: str, name: str) -> str | None:
    try:
        before, after = _find(original, name), _find(corrected, name)
    except SyntaxError as exc:
        return f"The corrected function is not valid Python: {exc.msg}"
    if after is None:
        return f"The corrected code must define '{name}'."
    if before is not None and _signature(before) != _signature(after):
        return "The correction changed the function's parameters. Keep the exact same signature."
    return None


def _feedback(v: dict) -> str:
    parts = [v["message"]]
    if v.get("regressions"):
        parts.append("Tests that now fail: " + ", ".join(v["regressions"][:10]))
    sec = v.get("security") or {}
    if sec.get("introduced"):
        parts.append(f"New security findings: {sec['introduced']}")
    if sec.get("fix_confirmed") is False:
        parts.append(f"The {sec.get('rule_id')} finding is still detected: untrusted input "
                     "still reaches the dangerous call. Use parameterized queries / safe APIs.")
    if v["status"] == "rejected":
        parts.append("Sandbox output:\n" + v["stdout"][-1500:] + v["stderr"][-800:])
    return "\n".join(parts)[:3000]


def _generate(req: VerifiedFixRequest, root: Path, rel: str, previous, feedback):
    target = _resolve_python_file(root, rel)
    try:
        creq = code_correction_service.create_request(
            file_path=target, function_name=req.function_name,
            finding=req.finding, severity=req.severity)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        ai = AICorrectionService(provider=FallbackCorrectionProvider()).correct(CorrectionInput(
            file_path=rel, function_name=req.function_name, original_code=creq.source_code,
            finding=req.finding, severity=req.severity, explanation=req.explanation,
            previous_attempt=previous, failure_feedback=feedback))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The AI provider could not generate a correction.") from exc
    try:
        return code_correction_service.create_result(creq, ai.corrected_code, ai.explanation)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/fix-verified", response_model=VerifiedFixResponse)
def fix_verified(request: VerifiedFixRequest) -> VerifiedFixResponse:
    """Generate a fix, test it in a Docker sandbox, retry on failure.
    Corrected code is returned ONLY if a candidate passes every check."""
    root, clone_workspace = _resolve_correction_repository(request.repository_path, request.github_url)
    rel = Path(request.file_path).as_posix()
    registered, attempts, last = False, [], None
    try:
        target = _resolve_python_file(root, rel)
        original_source = target.read_text(encoding="utf-8")
        original_hash = patch_registry.hash_source(original_source)
        rule_id = request.rule_id or infer_rule_id(request.finding, request.explanation)
        previous = feedback = None

        # Stage 1: explainer agent. Its analysis is handed to the fix agent and the AI reviewer.
        risk_explanation = _explain(request, root, rel)

        # Explainer sirf wahi finding dismiss kar sakta hai jise koi static rule support nahi karta.
        if (risk_explanation and risk_explanation.get("likely_false_positive") is True
                and not rule_id and not request.force_fix):
            return VerifiedFixResponse(
                status="likely_false_positive",
                message=("The explainer agent judged this finding a likely false positive and no "
                         "static rule confirms it, so no fix was attempted. "
                         "Send force_fix=true to try a fix anyway."),
                file_path=rel, function_name=request.function_name,
                risk_explanation=risk_explanation)

        if risk_explanation:
            request.explanation = (
                (request.explanation + "\n\n" if request.explanation else "")
                + "AI risk analysis: " + risk_explanation["why_risky"]
                + (" Fix strategy: " + risk_explanation["fix_strategy"] if risk_explanation["fix_strategy"] else "")
            )

        for n in range(1, request.max_attempts + 1):
            result = _generate(request, root, rel, previous, feedback)
            previous = result.corrected_code
            if patch_registry.hash_source(target.read_text(encoding="utf-8")) != original_hash:
                raise HTTPException(status_code=409, detail="The source changed during generation.")

            problem = _signature_problem(result.original_code, result.corrected_code, request.function_name)
            if problem is None and _is_unchanged(result.original_code, result.corrected_code):
                problem = ("The corrected code is identical to the original. "
                           "Make a real change that addresses the finding.")
            full = None
            if problem is None:
                try:
                    full = _build_updated_file(original_source, request.function_name,
                                               result.corrected_code, rel)
                except ValueError as exc:
                    problem = str(exc)
            if problem:
                attempts.append(Attempt(attempt=n, status="rejected", message=problem))
                feedback = problem
                continue

            v = verifier.verify(root, rel, full, rule_id=rule_id, function_name=request.function_name)
            last = v
            attempts.append(Attempt(attempt=n, status=v["status"], message=v["message"]))

            if v["status"] == "verified":
                review = ai_verifier.review(
                    function_name=request.function_name, finding=request.finding,
                    explanation=request.explanation, original_code=result.original_code,
                    corrected_code=result.corrected_code, sandbox_summary=v["message"])
                if review.verdict == "reject":
                    msg = "AI reviewer rejected the patch: " + review.reasoning
                    attempts[-1] = Attempt(attempt=n, status="rejected", message=msg)
                    feedback = msg
                    if review.new_risks:
                        feedback += "\nNew risks: " + "; ".join(review.new_risks)
                    continue
                tracked = patch_registry.register(repository_path=str(root), file_path=rel,
                                                  original_source=original_source, proposed_source=full)
                registered = True
                patch_registry.mark_verified(tracked.proposal_id, "verified")
                return VerifiedFixResponse(
                    status="verified", message=v["message"], proposal_id=tracked.proposal_id,
                    file_path=rel, function_name=request.function_name,
                    corrected_code=result.corrected_code, explanation=result.explanation,
                    patch=result.patch, verification=Verification(**v), attempts=attempts,
                    risk_explanation=risk_explanation, ai_review=review.to_dict())
            if v["status"] == "syntax_passed":
                break  # sandbox/re-scan unavailable: retrying cannot help
            feedback = _feedback(v)

        return VerifiedFixResponse(
            status="unverified",
            message="No candidate fix passed sandbox verification, so no corrected code is returned.",
            file_path=rel, function_name=request.function_name,
            verification=Verification(**last) if last else None, attempts=attempts,
            risk_explanation=risk_explanation)
    except (OSError, UnicodeDecodeError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if clone_workspace is not None and not registered:
            shutil.rmtree(clone_workspace, ignore_errors=True)