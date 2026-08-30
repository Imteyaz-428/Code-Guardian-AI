from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.api.schemas import AnalysisResponse
from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.risk.engine import RiskEngine


app = FastAPI(
    title="Code Guardian AI",
    description="Static code analysis and structural risk detection",
    version="0.1.0",
)
app = FastAPI(
    title="Code Guardian AI",
    description="Static code analysis and structural risk detection",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Code Guardian AI",
    }


@app.post("/analyze",response_model=AnalysisResponse)
def analyze_project(repository_path: str):

    try:
        analyzer = ProjectAnalyzer(repository_path)
        results = analyzer.analyze()

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    risk_engine = RiskEngine()

    findings = []

    for result in results:

        for metrics in result.metrics:

            finding = risk_engine.calculate_risk(metrics)

            findings.append({
                "file": result.file_path,
                "function": finding.function_name,
                "line": finding.line,
                "score": finding.score,
                "level": finding.level,
                "reasons": finding.reasons,
            })

    return {
        "summary": {
            "files_analyzed": len(results),
            "functions_analyzed": len(findings),
        },
        "findings": findings,
    }