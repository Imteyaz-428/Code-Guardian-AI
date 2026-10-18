from __future__ import annotations

import shutil
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.api.routes.pipeline import ScanFunction, ScanRequest, ai_explainer, gnn_service
from backend.api.routes.verified_fix import VerifiedFixRequest, fix_verified
from backend.repository.github import clone_github_repository
from backend.repository.manager import RepositoryManager
from backend.services.pipeline_runner import run_pipeline
from backend.services.sandbox_runner import SandboxUnavailable, get_sandbox_runner

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class RunRequest(ScanRequest):
    top_n: int = Field(default=10, ge=1, le=100)
    explain_top: int = Field(default=3, ge=0, le=10)
    fix_top: int = Field(default=1, ge=0, le=5, description="How many risky functions to auto-fix.")
    min_fix_risk: float = Field(default=50, ge=0, le=100, description="Only fix functions at or above this risk %.")
    fix_structural: bool = Field(default=False, description="Also try refactors for complexity-only functions.")
    max_attempts: int = Field(default=3, ge=1, le=5)


class RunFunction(ScanFunction):
    fix_status: str = "not_attempted"   # verified | unverified | skipped | blocked | error | ...
    fix_message: str = ""
    fix: dict[str, Any] | None = None   # corrected_code, patch, verification, ai_review ...


class RunResponse(BaseModel):
    summary: dict[str, Any]
    gnn_note: str = ""
    score_note: str
    functions: list[RunFunction]


def _sandbox_blocker() -> str | None:
    """Why fixes can't be verified right now (None = sandbox is ready)."""
    try:
        get_sandbox_runner()
        return None
    except SandboxUnavailable as exc:
        return f"sandbox unavailable: {exc}"


def _fix(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return fix_verified(VerifiedFixRequest(**payload)).model_dump()
    except HTTPException as exc:
        return {"status": "error", "message": str(exc.detail)}
    except Exception as exc:
        return {"status": "error", "message": f"{type(exc).__name__}: {exc}"}


@router.post("/run", response_model=RunResponse)
def run_full_pipeline(request: RunRequest) -> RunResponse:
    """URL or path -> static risk + GNN risk -> fused risk % -> explainer ->
    fix agent -> sandbox verification -> verified corrected code."""
    clone_workspace = None
    keep_workspace = False

    try:
        if request.github_url:
            repository_path, clone_workspace = clone_github_repository(request.github_url)
            origin = {"github_url": request.github_url}
        else:
            repository_path = request.repository_path
            origin = {"repository_path": request.repository_path}

        repository = RepositoryManager(repository_path)
        if not repository.validate_repository():
            raise ValueError("Repository directory does not exist.")

        analyzer = ProjectAnalyzer(repository.repository_path)
        results = analyzer.analyze()

        data = run_pipeline(
            analyzer, results, repository.repository_path,
            origin=origin,
            gnn_service=gnn_service if request.use_gnn else None,
            explainer=ai_explainer if request.explain_top else None,
            fix_callable=_fix,
            preflight=_sandbox_blocker,
            top_n=request.top_n, explain_top=request.explain_top,
            fix_top=request.fix_top, min_fix_risk=request.min_fix_risk,
            fix_structural=request.fix_structural, max_attempts=request.max_attempts,
        )

        # Verified patches are registered against this clone; keep it so
        # /correction/{id}/approve and /correction/apply can still work.
        keep_workspace = data.pop("any_verified")
        return RunResponse(**data)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Unable to access repository: {exc}") from exc
    finally:
        if clone_workspace is not None and not keep_workspace:
            shutil.rmtree(clone_workspace, ignore_errors=True)