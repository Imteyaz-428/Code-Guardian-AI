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



# Call Graph schemas



class CallGraphEdge(BaseModel):
    caller: str
    callee: str


class CallGraphResponse(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    edges: list[CallGraphEdge] = Field(default_factory=list)



# Control Flow Graph schemas



class CFGNode(BaseModel):
    id: int
    type: str
    label: str
    line: int | None = None


class CFGResponse(BaseModel):
    function: str
    nodes: list[CFGNode] = Field(default_factory=list)
    edges: list[tuple[int, int]] = Field(default_factory=list)



# Analysis schemas



class AnalysisSummary(BaseModel):
    files_analyzed: int
    functions_analyzed: int
    files_failed: int = 0


class AnalysisResponse(BaseModel):
    summary: AnalysisSummary

    findings: list[Finding]

    errors: list[str] = Field(
        default_factory=list
    )

    call_graph: CallGraphResponse = Field(
        default_factory=CallGraphResponse
    )

    control_flow_graphs: list[CFGResponse] = Field(
        default_factory=list
    )