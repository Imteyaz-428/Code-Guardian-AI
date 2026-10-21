from typing import Any

from pydantic import BaseModel, Field, model_validator


class AnalyzeRequest(BaseModel):
    repository_path: str | None = Field(
        default=None,
        min_length=1,
        description="Local repository path within the configured analysis root.",
    )

    github_url: str | None = Field(
        default=None,
        min_length=1,
        description="HTTPS URL of a public GitHub repository.",
    )

    @model_validator(mode="after")
    def validate_repository_source(self):
        if bool(self.repository_path) == bool(self.github_url):
            raise ValueError(
                "Provide exactly one of repository_path or github_url."
            )

        return self

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


class GNNPrediction(BaseModel):
    model: str = "CleanVulGraphClassifier"

    class_id: int
    label: str

    probabilities: dict[str, float]

    graph: dict[str, int]

    warning: str


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

    # Unified Code Graph
    unified_code_graph: dict[str, Any] = Field(
        default_factory=dict
    )

    # Static-analysis risk labels
    risk_labels: Any = None

    # Experimental GNN prediction
    gnn_prediction: GNNPrediction | None = None

    # Extended static-analysis details. Optional/defaulted so existing
    # clients and the frozen React dashboard remain backward-compatible.
    analysis_summary: dict[str, Any] = Field(default_factory=dict)
    data_flow_findings: list[dict[str, Any]] = Field(default_factory=list)
    dead_definition_findings: list[dict[str, Any]] = Field(default_factory=list)
    taint_findings: list[dict[str, Any]] = Field(default_factory=list)
    vulnerability_findings: list[dict[str, Any]] = Field(default_factory=list)
    finding_counts: dict[str, int] = Field(default_factory=dict)
    
# ---------------------------------------------------------
# AI Code Correction Schemas
# ---------------------------------------------------------

class CorrectionRequest(BaseModel):
    repository_path: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Local repository path within the configured analysis root."
        ),
    )

    github_url: str | None = Field(
        default=None,
        min_length=1,
        description="HTTPS URL of a public GitHub repository.",
    )

    file_path: str = Field(
        ...,
        min_length=1,
        description="Python file path relative to the repository root.",
    )

    function_name: str = Field(
        ...,
        min_length=1,
        description="Name of the function to correct.",
    )

    finding: str = Field(
        ...,
        min_length=1,
        description="Description of the finding to address.",
    )

    severity: str = Field(
        default="medium",
        description="Finding severity.",
    )

    explanation: str = Field(
        default="",
        description="Additional context from static analysis.",
    )

    @model_validator(mode="after")
    def validate_repository_source(self):
        if bool(self.repository_path) == bool(self.github_url):
            raise ValueError(
                "Provide exactly one of repository_path or github_url."
            )

        return self


class CorrectionResponse(BaseModel):
    file_path: str
    function_name: str
    original_code: str
    corrected_code: str
    explanation: str
    patch: str
    status: str = "proposed"