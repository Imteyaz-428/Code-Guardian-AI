from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.api.schemas import AnalysisResponse, AnalyzeRequest
from backend.repository.manager import RepositoryManager

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_project(request: AnalyzeRequest) -> AnalysisResponse:
    """Analyze a repository and return function-level structural risk findings."""
    try:
        repository = RepositoryManager(request.repository_path)
        analyzer = ProjectAnalyzer(repository.repository_path)
        results = analyzer.analyze()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Unable to access repository: {exc}") from exc

    root = repository.repository_path.resolve()
    findings = []
    from backend.analysis.risk_engine import RiskEngine
    risk_engine = RiskEngine(repository_path=root)

    for result in results:
        file_path = Path(result.file_path).resolve()
        try:
            display_path = file_path.relative_to(root).as_posix()
        except ValueError:
            display_path = result.file_path

        for metrics in result.metrics:
            finding = risk_engine.calculate_function_risk(metrics)
            findings.append(
                {
                    "file": display_path,
                    "function": finding["name"],
                    "line": finding["line"],
                    "score": finding["score"],
                    "level": finding["level"],
                    "reasons": finding["reasons"],
                }
            )

    return AnalysisResponse(
        summary={
            "files_analyzed": len(results),
            "functions_analyzed": len(findings),
            "files_failed": len(analyzer.errors),
        },
        findings=findings,
        errors=analyzer.errors,
    )
