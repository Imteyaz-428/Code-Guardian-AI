from pydantic import BaseModel


class SummaryResponse(BaseModel):
    files_analyzed: int
    functions_analyzed: int


class FindingResponse(BaseModel):
    file: str
    function: str
    line: int
    score: float
    level: str
    reasons: list[str]


class AnalysisResponse(BaseModel):
    summary: SummaryResponse
    findings: list[FindingResponse]