from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repository_path: str = Field(
        ...,
        min_length=1,
        description=(
            "Path to the repository relative to the configured analysis root."
        ),
    )


class Finding(BaseModel):
    file: str
    function: str
    line: int
    score: int
    level: str
    reasons: list[str]


class AnalysisSummary(BaseModel):
    files_analyzed: int
    functions_analyzed: int
    files_failed: int = 0


class AnalysisResponse(BaseModel):
    summary: AnalysisSummary
    findings: list[Finding]
    errors: list[str] = Field(default_factory=list)
