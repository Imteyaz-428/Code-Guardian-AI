"""One pipeline: scan -> fuse risk -> explain -> fix -> verify -> corrected code.

Pure Python (no web framework) so it can be tested with fakes.  The route
passes in the real analyzer, GNN service, explainer and fix function.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from backend.services.risk_fusion import build_scan, function_source

FIX_KEYS = (
    "status", "message", "proposal_id", "corrected_code", "explanation",
    "patch", "verification", "attempts", "ai_review",
)


def run_pipeline(
    analyzer,
    results,
    root: Path,
    *,
    origin: dict[str, str],
    gnn_service,
    explainer,
    fix_callable: Callable[[dict[str, Any]], dict[str, Any]],
    top_n: int = 10,
    explain_top: int = 3,
    fix_top: int = 1,
    min_fix_risk: float = 50.0,
    fix_structural: bool = False,
    max_attempts: int = 3,
    preflight: Callable[[], str | None] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()

    # 1-3. static risk + GNN risk + fusion (one analysis, one GNN pass)
    scan = build_scan(
        analyzer, results, root,
        gnn_service=gnn_service,
        explainer=None,                       # explained below, once per function
        repo_ref={"repository_path": str(root)},
        top_n=top_n, explain_top=0,
    )
    rows = scan["functions"]

    attempted = verified = 0

    # Check the sandbox BEFORE spending any AI quota on fixes.
    blocker = preflight() if preflight else None

    # 4-6. fix agent -> sandbox + security re-scan + AI review
    for row in rows:
        row["fix_status"], row["fix_message"], row["fix"] = "not_attempted", "", None

        if row["final_risk_percent"] < min_fix_risk:
            row["fix_status"] = "skipped"
            row["fix_message"] = f"Risk is below min_fix_risk ({min_fix_risk:g}%)."
            continue

        if not row["vulnerability_score"] and not fix_structural:
            row["fix_status"] = "skipped"
            row["fix_message"] = (
                "No confirmed vulnerability (complexity signals only). "
                "Set fix_structural=true to try a refactor anyway."
            )
            continue

        if attempted >= fix_top:
            row["fix_status"] = "skipped"
            row["fix_message"] = f"fix_top limit ({fix_top}) reached."
            continue

        if blocker:
            row["fix_status"] = "blocked"
            row["fix_message"] = f"Fix not attempted (no AI calls used): {blocker}"
            continue

        attempted += 1
        payload = {k: v for k, v in row["fix_request"].items() if v is not None}
        payload["max_attempts"] = max_attempts

        fix = fix_callable(payload)

        row["fix_status"] = fix.get("status", "error")
        row["fix_message"] = fix.get("message", "")
        row["fix"] = {k: fix.get(k) for k in FIX_KEYS}

        if fix.get("risk_explanation"):
            row["explanation"] = fix["risk_explanation"]

        if row["fix_status"] == "verified":
            verified += 1

    # explainer agent for the top functions that the fix stage did not explain
    if explainer is not None:
        for row in rows[:explain_top]:
            if row["explanation"] is not None or row["level"] == "LOW":
                continue                      # already explained / not worth an AI call
            code = function_source(analyzer, row["function_id"], root)
            if not code:
                continue
            fix_req = row["fix_request"]
            exp = explainer.explain(
                file_path=row["file"], function_name=row["function"], code=code,
                severity=fix_req["severity"], finding=fix_req["finding"],
                static_explanation=fix_req["explanation"],
            )
            row["explanation"] = exp.to_dict() if exp else None

    # point fix_request at what the user originally gave (not a temp clone)
    for row in rows:
        row["fix_request"].pop("repository_path", None)
        row["fix_request"].update(origin)

    scan["summary"].update({
        "fixes_attempted": attempted,
        "fixes_verified": verified,
    })
    scan["any_verified"] = verified > 0
    return scan