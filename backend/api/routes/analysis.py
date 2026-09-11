from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.api.schemas import AnalysisResponse, AnalyzeRequest
from backend.repository.manager import RepositoryManager
from backend.analysis.risk_engine import RiskEngine


router = APIRouter(tags=["analysis"])


def _normalize_function_id(function_id: str, root: Path) -> str:
    """
    Convert an absolute-path function ID into a repository-relative ID.

    Example:

        /project/auth.py::login

    becomes:

        auth.py::login
    """

    parts = function_id.split("::")

    file_path = Path(parts[0]).resolve()

    try:
        relative_file = file_path.relative_to(root).as_posix()
    except ValueError:
        relative_file = parts[0]

    if len(parts) == 1:
        return relative_file

    return "::".join([relative_file, *parts[1:]])


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_project(request: AnalyzeRequest) -> AnalysisResponse:
    """Analyze a repository and return structural analysis results."""

   
    # Run repository analysis
   

    try:
        repository = RepositoryManager(request.repository_path)
        analyzer = ProjectAnalyzer(repository.repository_path)
        results = analyzer.analyze()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to access repository: {exc}",
        ) from exc

    root = repository.repository_path.resolve()

   
    # Risk findings
   

    findings = []

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

   
    # Call Graph
   

    call_graph = {
        "nodes": [],
        "edges": [],
    }

    if analyzer.call_graph is not None:
        call_graph["nodes"] = [
            _normalize_function_id(function_id, root)
            for function_id in analyzer.call_graph.get_all_functions()
        ]

        call_graph["edges"] = [
            {
                "caller": _normalize_function_id(caller, root),
                "callee": _normalize_function_id(callee, root),
            }
            for caller, callee in analyzer.call_graph.get_edges()
        ]

   
    # Control Flow Graphs
   

    control_flow_graphs = []

    for function_id, cfg in analyzer.control_flow_graphs.items():
        control_flow_graphs.append(
            {
                "function": _normalize_function_id(
                    function_id,
                    root,
                ),
                "nodes": [
                    node.to_dict()
                    for node in cfg.get_nodes()
                ],
                "edges": [
                    list(edge)
                    for edge in cfg.get_edges()
                ],
            }
        )

   
    # Final API response
   

    return AnalysisResponse(
        summary={
            "files_analyzed": len(results),
            "functions_analyzed": len(findings),
            "files_failed": len(analyzer.errors),
        },
        findings=findings,
        errors=analyzer.errors,
        call_graph=call_graph,
        control_flow_graphs=control_flow_graphs,
    )