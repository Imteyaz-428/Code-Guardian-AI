from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    name: str
    line: int
    parameters: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    line: int


@dataclass
class FunctionMetrics:
    name: str
    line: int

    lines_of_code: int = 0
    parameters: int = 0
    branches: int = 0
    loops: int = 0
    function_calls: int = 0
    nesting_depth: int = 0
    cyclomatic_complexity: int = 1
    

@dataclass
class AnalysisResult:
    file_path: str

    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    function_calls: list[str] = field(default_factory=list)

    conditions: int = 0
    loops: int = 0
    returns: int = 0

    metrics: list[FunctionMetrics] = field(default_factory=list)
    
@dataclass
class RiskFinding:
    function_name: str
    line: int

    score: float
    level: str

    reasons: list[str] = field(default_factory=list)