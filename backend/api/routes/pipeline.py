from __future__ import annotations

import shutil
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.api.schemas import AnalyzeRequest
from backend.ml.cvefixes_inference import CVEFixesInferenceService
from backend.repository.github import clone_github_repository
from backend.repository.manager import RepositoryManager
from backend.services.ai_explainer import AIExplainerService
from backend.services.risk_fusion import build_scan

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

gnn_service = CVEFixesInferenceService()
ai_explainer = AIExplainerService()


class ScanRequest(AnalyzeRequest):
    top_n: int = Field(default=15, ge=1, le=100, description="How many risky functions to return.")
    explain_top: int = Field(default=3, ge=0, le=10, description="Explainer agent runs on the top N.")
    min_final_risk: float = Field(default=0, ge=0, le=100)
    use_gnn: bool = True


class ScanFunction(BaseModel):
    rank: int
    file: str
    function: str
    function_id: str
    line: int
    final_risk_percent: float
    level: str
    static_risk_percent: float
    structural_score: int
    vulnerability_score: int
    gnn_risk_percent: float | None = None
    gnn_label: str | None = None
    basis: str
    reasons: list[str] = Field(default_factory=list)
    vulnerabilities: list[dict[str, Any]] = Field(default_factory=list)
    explanation: dict | None = None  # explainer agent output
    fix_request: dict[str, Any]      # POST this to /correction/fix-verified


class ScanResponse(BaseModel):
    summary: dict[str, Any]
    gnn_note: str = ""
    score_note: str
    functions: list[ScanFunction]


@router.post("/scan", response_model=ScanResponse)
def scan_repository(request: ScanRequest) -> ScanResponse:
    """Repository URL -> static + GNN risk per function -> fused risk % ->
    explainer agent for the top functions.  Nothing is modified."""
    clone_workspace = None

    try:
        if request.github_url:
            repository_path, clone_workspace = clone_github_repository(request.github_url)
            repo_ref = {"github_url": request.github_url}
        else:
            repository_path = request.repository_path
            repo_ref = {"repository_path": request.repository_path}

        repository = RepositoryManager(repository_path)
        if not repository.validate_repository():
            raise ValueError("Repository directory does not exist.")

        analyzer = ProjectAnalyzer(repository.repository_path)
        results = analyzer.analyze()

        data = build_scan(
            analyzer, results, repository.repository_path,
            gnn_service=gnn_service if request.use_gnn else None,
            explainer=ai_explainer if request.explain_top else None,
            repo_ref=repo_ref,
            top_n=request.top_n,
            explain_top=request.explain_top,
            min_final_risk=request.min_final_risk,
        )
        return ScanResponse(**data)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Unable to access repository: {exc}") from exc
    finally:
        if clone_workspace is not None:
            shutil.rmtree(clone_workspace, ignore_errors=True)