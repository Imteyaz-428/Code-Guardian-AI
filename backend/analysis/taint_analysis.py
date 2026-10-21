"""
Taint Analysis for Code Guardian AI.

Combined milestone:

    v3 - Sanitizers
    v4 - Vulnerability classification
    v5 - Interprocedural propagation

The analyzer supports two levels:

1. Function-level analysis

       TaintAnalyzer.analyze(...)

2. Project-level analysis

       TaintAnalyzer.analyze_project(...)

The existing function-level API is preserved so the previous
taint-analysis tests continue to work.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from backend.analysis import taint_catalog as catalog
from backend.analysis.data_flow import DataFlowResult
from backend.analysis.def_use import DefUseResult
from backend.analysis.vulnerability_rules import (
    VulnerabilityFinding,
    VulnerabilityRuleEngine,
)


# ================================================================
# SOURCE
# ================================================================


@dataclass(frozen=True)
class TaintSource:
    """A source of potentially untrusted data."""

    name: str
    line: int
    kind: str = "source"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "line": self.line,
            "kind": self.kind,
        }


# ================================================================
# SANITIZER
# ================================================================


@dataclass(frozen=True)
class TaintSanitizer:
    """A function that removes or neutralizes taint."""

    name: str
    line: int
    kind: str = "sanitizer"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "line": self.line,
            "kind": self.kind,
        }


# ================================================================
# SINK
# ================================================================


@dataclass(frozen=True)
class TaintSink:
    """A sensitive operation receiving data."""

    name: str
    line: int
    kind: str = "sink"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "line": self.line,
            "kind": self.kind,
        }


# ================================================================
# TAINT FLOW
# ================================================================


@dataclass(frozen=True)
class TaintFlowFinding:
    """Represents one source-to-sink taint flow."""

    source_name: str
    source_line: int

    sink_name: str
    sink_line: int

    variable: str

    definition_id: str = ""
    use_id: str = ""

    path: tuple[str, ...] = ()

    reason: str = (
        "Potentially tainted data flows from a source "
        "to a sensitive sink."
    )

    # Where the sink physically is (set by the project-level engine).
    file: str = ""
    function: str = ""
    function_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_line": self.source_line,
            "sink_name": self.sink_name,
            "sink_line": self.sink_line,
            "variable": self.variable,
            "definition_id": self.definition_id,
            "use_id": self.use_id,
            "path": list(self.path),
            "reason": self.reason,
            "file": self.file,
            "function": self.function,
            "function_id": self.function_id,
        }


# ================================================================
# RESULT
# ================================================================


@dataclass
class TaintAnalysisResult:
    """Complete taint-analysis result."""

    function_name: str

    sources: list[TaintSource] = field(
        default_factory=list
    )

    sanitizers: list[TaintSanitizer] = field(
        default_factory=list
    )

    sinks: list[TaintSink] = field(
        default_factory=list
    )

    findings: list[TaintFlowFinding] = field(
        default_factory=list
    )

    vulnerabilities: list[VulnerabilityFinding] = field(
        default_factory=list
    )

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def vulnerability_count(self) -> int:
        return len(self.vulnerabilities)

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "function": self.function_name,
            "sources": [
                source.to_dict()
                for source in self.sources
            ],
            "sanitizers": [
                sanitizer.to_dict()
                for sanitizer in self.sanitizers
            ],
            "sinks": [
                sink.to_dict()
                for sink in self.sinks
            ],
            "finding_count": self.finding_count,
            "vulnerability_count": self.vulnerability_count,
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
            "vulnerabilities": [
                vulnerability.to_dict()
                for vulnerability in self.vulnerabilities
            ],
        }


# ================================================================
# INTERNAL TAINT STATE
# ================================================================


@dataclass(frozen=True)
class _TaintOrigin:
    source_name: str
    source_line: int
    # Rule ids this value is already safe for (e.g. Path(x).suffix cannot
    # contain "../", so it is neutralised for PATH_TRAVERSAL only).
    neutralized: frozenset = frozenset()


# ================================================================
# ANALYZER
# ================================================================


class TaintAnalyzer:
    """
    Combined taint analyzer.

    Supports:

        source -> variable
        variable -> variable
        variable -> expression
        expression -> sink

    plus:

        sanitizer handling
        vulnerability classification
        project-level interprocedural propagation
    """

    DEFAULT_SOURCE_NAMES = {
        "input",
        "request_input",
        "get_user_input",
    }

    DEFAULT_SANITIZER_NAMES = {
        "sanitize",
        "escape",
        "escape_sql",
        "html_escape",
        "sanitize_sql",
        "sanitize_html",
        "quote",
        "quote_plus",
        "int",
        "float",
        "bool",
        "clean",
        "escape_string",
    }

    DEFAULT_SINK_NAMES = {
        "execute",
        "execute_query",
        "run_command",
    }

    def __init__(
        self,
        vulnerability_engine: VulnerabilityRuleEngine | None = None,
    ) -> None:
        self.vulnerability_engine = (
            vulnerability_engine
            if vulnerability_engine is not None
            else VulnerabilityRuleEngine()
        )
        self._use_catalog_sinks = True
        self._node_ids: dict[int, str] = {}
        self._function_stack: list[str] = []
        self._node_stack: list[int] = []
        self._argv_frames: list[set[str]] = []
        self._return_shapes: dict[int, tuple] = {}
        self._return_cache: dict[tuple, tuple] = {}
        self._sink_names: set[str] = set()

    # ============================================================
    # FUNCTION-LEVEL ANALYSIS
    # ============================================================

    def analyze(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        data_flow: DataFlowResult,
        def_use: DefUseResult,
        source_names: Optional[Iterable[str]] = None,
        sink_names: Optional[Iterable[str]] = None,
        sanitizer_names: Optional[Iterable[str]] = None,
    ) -> TaintAnalysisResult:
        """
        Analyze one function.

        Existing callers remain compatible because all new options
        are optional.
        """

        sources = set(
            source_names
            if source_names is not None
            else self.DEFAULT_SOURCE_NAMES
        )

        sanitizers = set(
            sanitizer_names
            if sanitizer_names is not None
            else self.DEFAULT_SANITIZER_NAMES
        )

        sinks = set(
            sink_names
            if sink_names is not None
            else self.DEFAULT_SINK_NAMES
        )

        function_name = self._function_name(
            data_flow.function_id
        )

        result = TaintAnalysisResult(
            function_name=function_name
        )

        result.sources = self._find_sources(
            function_node,
            sources,
        )

        result.sanitizers = self._find_sanitizers(
            function_node,
            sanitizers,
        )

        result.sinks = self._find_sinks(
            function_node,
            sinks,
        )

        if not result.sources or not result.sinks:
            return result

        definition_ids = self._build_definition_id_map(
            data_flow
        )

        tainted: dict[str, _TaintOrigin] = {}

        self._analyze_statements(
            statements=function_node.body,
            tainted=tainted,
            source_names=sources,
            sanitizer_names=sanitizers,
            sink_names=sinks,
            result=result,
            data_flow=data_flow,
            def_use=def_use,
            definition_ids=definition_ids,
        )

        return result

    # ============================================================
    # PROJECT-LEVEL INTERPROCEDURAL ANALYSIS
    # ============================================================

    def analyze_project(
        self,
        functions: dict[
            str,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ],
        source_names: Optional[Iterable[str]] = None,
        sink_names: Optional[Iterable[str]] = None,
        sanitizer_names: Optional[Iterable[str]] = None,
    ) -> TaintAnalysisResult:
        """
        Perform project-level interprocedural taint analysis.

        `functions` maps a function identifier to its AST node.

        Example:

            {
                "main": main_function_node,
                "get_input": get_input_node,
                "execute_query": execute_query_node,
            }

        The analyzer resolves direct calls between functions and
        propagates taint through arguments and return values.

        This is intentionally a lightweight first interprocedural
        implementation. It does not yet require the existing
        CallGraph object.
        """

        sources = set(
            source_names
            if source_names is not None
            else self.DEFAULT_SOURCE_NAMES
        )

        sanitizers = set(
            sanitizer_names
            if sanitizer_names is not None
            else self.DEFAULT_SANITIZER_NAMES
        )

        sinks = set(
            sink_names
            if sink_names is not None
            else self.DEFAULT_SINK_NAMES
        )

        combined = TaintAnalysisResult(
            function_name="<project>"
        )

        # Catalog sinks apply unless the caller supplied its own sink names.
        self._use_catalog_sinks = sink_names is None
        self._node_ids = {
            id(function_node): function_id
            for function_id, function_node in functions.items()
        }
        self._function_stack = []
        self._node_stack = []
        self._argv_frames = []
        self._return_shapes = {}
        self._return_cache = {}
        self._sink_names = sinks

        function_by_name: dict[
            str,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ] = {}

        for function_id, function_node in functions.items():
            function_by_name[
                function_node.name
            ] = function_node

        # --------------------------------------------------------
        # Discover project sources, sanitizers and sinks.
        # --------------------------------------------------------

        for function_node in functions.values():

            combined.sources.extend(
                self._find_sources(
                    function_node,
                    sources,
                )
            )

            combined.sanitizers.extend(
                self._find_sanitizers(
                    function_node,
                    sanitizers,
                )
            )

            combined.sinks.extend(
                self._find_sinks(
                    function_node,
                    sinks,
                )
            )

        # --------------------------------------------------------
        # Analyze each function with summaries.
        # --------------------------------------------------------

        summaries: dict[
            str,
            bool,
        ] = {}

        for function_name, function_node in (
            function_by_name.items()
        ):
            summaries[function_name] = self._function_returns_taint(
                function_node=function_node,
                source_names=sources,
                sanitizer_names=sanitizers,
            )

        # --------------------------------------------------------
        # Analyze project flows.
        # --------------------------------------------------------

        # Every function is analysed (same-named functions in different
        # files included). Route-handler parameters are attacker-controlled.
        for function_id, function_node in functions.items():

            state: dict[str, _TaintOrigin] = {}

            if catalog.is_route_handler(function_node):
                for parameter in catalog.route_parameters(function_node):
                    state[parameter] = _TaintOrigin(
                        source_name="route_parameter",
                        source_line=getattr(function_node, "lineno", 0),
                    )

            self._execute_interprocedural(
                function_node=function_node,
                tainted=state,
                function_by_name=function_by_name,
                source_names=sources,
                sanitizer_names=sanitizers,
                sink_names=sinks,
                result=combined,
                summaries=summaries,
            )

        self._dedupe(combined)

        return combined

    # ============================================================
    # STATEMENT ANALYSIS
    # ============================================================

    def _analyze_statements(
        self,
        statements: list[ast.stmt],
        tainted: dict[str, _TaintOrigin],
        source_names: set[str],
        sanitizer_names: set[str],
        sink_names: set[str],
        result: TaintAnalysisResult,
        data_flow: DataFlowResult,
        def_use: DefUseResult,
        definition_ids: dict[tuple[str, int], str],
    ) -> None:

        for statement in statements:

            # ----------------------------------------------------
            # ASSIGNMENT
            # ----------------------------------------------------

            if isinstance(statement, ast.Assign):

                origin = self._expression_taint(
                    statement.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                for target in statement.targets:
                    self._assign_taint(
                        target,
                        origin,
                        tainted,
                    )

                self._check_sinks_in_expression(
                    statement.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                continue

            # ----------------------------------------------------
            # ANNOTATED ASSIGNMENT
            # ----------------------------------------------------

            if isinstance(statement, ast.AnnAssign):

                origin = None

                if statement.value is not None:
                    origin = self._expression_taint(
                        statement.value,
                        tainted,
                        source_names,
                        sanitizer_names,
                    )

                    self._check_sinks_in_expression(
                        statement.value,
                        tainted,
                        source_names,
                        sanitizer_names,
                        sink_names,
                        result,
                        data_flow,
                        def_use,
                        definition_ids,
                    )

                self._assign_taint(
                    statement.target,
                    origin,
                    tainted,
                )

                continue

            # ----------------------------------------------------
            # AUGMENTED ASSIGNMENT
            # ----------------------------------------------------

            if isinstance(statement, ast.AugAssign):

                existing = None

                if isinstance(
                    statement.target,
                    ast.Name,
                ):
                    existing = tainted.get(
                        statement.target.id
                    )

                value_origin = self._expression_taint(
                    statement.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                origin = (
                    existing
                    if existing is not None
                    else value_origin
                )

                self._assign_taint(
                    statement.target,
                    origin,
                    tainted,
                )

                continue

            # ----------------------------------------------------
            # IF
            # ----------------------------------------------------

            if isinstance(statement, ast.If):

                self._check_sinks_in_expression(
                    statement.test,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                true_state = dict(tainted)
                false_state = dict(tainted)

                self._analyze_statements(
                    statement.body,
                    true_state,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                self._analyze_statements(
                    statement.orelse,
                    false_state,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                merged = dict(tainted)

                for name, origin in true_state.items():
                    merged.setdefault(
                        name,
                        origin,
                    )

                for name, origin in false_state.items():
                    merged.setdefault(
                        name,
                        origin,
                    )

                tainted.clear()
                tainted.update(merged)

                continue

            # ----------------------------------------------------
            # LOOPS
            # ----------------------------------------------------

            if isinstance(
                statement,
                (
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                ),
            ):

                if isinstance(
                    statement,
                    ast.While,
                ):
                    expression = statement.test
                else:
                    expression = statement.iter

                self._check_sinks_in_expression(
                    expression,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                loop_state = dict(tainted)

                self._analyze_statements(
                    statement.body,
                    loop_state,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                for name, origin in loop_state.items():
                    tainted.setdefault(
                        name,
                        origin,
                    )

                self._analyze_statements(
                    statement.orelse,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                continue

            # ----------------------------------------------------
            # RETURN
            # ----------------------------------------------------

            if isinstance(statement, ast.Return):

                if statement.value is not None:
                    self._check_sinks_in_expression(
                        statement.value,
                        tainted,
                        source_names,
                        sanitizer_names,
                        sink_names,
                        result,
                        data_flow,
                        def_use,
                        definition_ids,
                    )

                continue

            # ----------------------------------------------------
            # TRY
            # ----------------------------------------------------

            if isinstance(statement, ast.Try):

                self._analyze_statements(
                    statement.body,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                for handler in statement.handlers:
                    self._analyze_statements(
                        handler.body,
                        tainted,
                        source_names,
                        sanitizer_names,
                        sink_names,
                        result,
                        data_flow,
                        def_use,
                        definition_ids,
                    )

                self._analyze_statements(
                    statement.orelse,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                self._analyze_statements(
                    statement.finalbody,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                continue

            # ----------------------------------------------------
            # EXPRESSION
            # ----------------------------------------------------

            if isinstance(statement, ast.Expr):

                self._check_sinks_in_expression(
                    statement.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

    # ============================================================
    # EXPRESSION TAINT
    # ============================================================

    def _expression_taint(
        self,
        node: ast.AST,
        tainted: dict[str, _TaintOrigin],
        source_names: set[str],
        sanitizer_names: set[str],
    ) -> Optional[_TaintOrigin]:
        """
        Determine whether an expression contains tainted data.

        Recognizes configured sources and common framework request
        inputs while ensuring sanitizer calls stop taint propagation.
        """

        # Direct variable reference.
        if isinstance(node, ast.Name):
            return tainted.get(node.id)

        # request.args["x"], request.form, sys.argv[1], ...
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            attribute_source = catalog.expression_source(node)

            if attribute_source is not None:
                return _TaintOrigin(
                    source_name=attribute_source,
                    source_line=getattr(node, "lineno", 0),
                )

        if isinstance(node, ast.Attribute) and node.attr in self.PATH_NEUTRAL_ATTRS:
            return self._neutralize(
                self._expression_taint(
                    node.value, tainted, source_names, sanitizer_names,
                ),
                "PATH_TRAVERSAL",
            )

        # Handle function and method calls.
        if isinstance(node, ast.Call):
            call_name = self._call_name(node)

            # A sanitizer must stop propagation before its arguments
            # are inspected.
            if call_name in sanitizer_names:
                return None

            if call_name in self.PATH_NEUTRAL_CALLS:
                return self._neutralize(
                    self._pick(
                        self._expression_taint(a, tainted, source_names, sanitizer_names)
                        for a in node.args
                    ),
                    "PATH_TRAVERSAL",
                )

            # Recognize direct sources and framework request inputs.
            source_name = self._source_name_for_call(
                node,
                source_names,
            )

            if source_name is not None:
                return _TaintOrigin(
                    source_name=source_name,
                    source_line=getattr(node, "lineno", 0),
                )

            # Propagate taint through arguments of ordinary calls.
            for argument in node.args:
                origin = self._expression_taint(
                    argument,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                if origin is not None:
                    return origin

            # Propagate taint through method receivers, such as
            # username.strip() or username.lower().
            if isinstance(node.func, ast.Attribute):
                origin = self._expression_taint(
                    node.func.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                if origin is not None:
                    return origin

            for keyword in node.keywords:
                origin = self._expression_taint(
                    keyword.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                if origin is not None:
                    return origin

            return None

        # Inspect compound expressions, including concatenation,
        # formatted strings, and binary operations.
        return self._pick(
            self._expression_taint(
                child,
                tainted,
                source_names,
                sanitizer_names,
            )
            for child in ast.iter_child_nodes(node)
        )
    # ============================================================
    # SOURCE
    # ============================================================

    @staticmethod
    def _source_origin_from_call(
        node: ast.AST,
        source_names: set[str],
    ) -> Optional[_TaintOrigin]:
        """Resolve direct and framework-specific taint sources."""

        if not isinstance(node, ast.Call):
            return None

        name = TaintAnalyzer._source_name_for_call(
            node,
            source_names,
        )

        if name is None:
            return None

        return _TaintOrigin(
            source_name=name,
            source_line=getattr(node, "lineno", 0),
        )

    # ============================================================
    # ASSIGNMENT
    # ============================================================

    @staticmethod
    def _assign_taint(
        target: ast.AST,
        origin: Optional[_TaintOrigin],
        tainted: dict[str, _TaintOrigin],
    ) -> None:

        if isinstance(
            target,
            ast.Name,
        ):

            if origin is None:
                tainted.pop(
                    target.id,
                    None,
                )
            else:
                tainted[target.id] = origin

            return

        if isinstance(
            target,
            (
                ast.Tuple,
                ast.List,
            ),
        ):

            for element in target.elts:
                TaintAnalyzer._assign_taint(
                    element,
                    origin,
                    tainted,
                )

            return

        # data["key"] = tainted  /  obj.attr = tainted  -> container is tainted
        if isinstance(target, (ast.Subscript, ast.Attribute)) and origin is not None:
            root, _ = catalog._chain(target)

            if root is not None:
                tainted.setdefault(root, origin)

    # ============================================================
    # SINK DETECTION
    # ============================================================

    def _check_sinks_in_expression(
        self,
        node: ast.AST,
        tainted: dict[str, _TaintOrigin],
        source_names: set[str],
        sanitizer_names: set[str],
        sink_names: set[str],
        result: TaintAnalysisResult,
        data_flow: DataFlowResult,
        def_use: DefUseResult,
        definition_ids: dict[tuple[str, int], str],
    ) -> None:

        for ast_node in ast.walk(node):

            if not isinstance(
                ast_node,
                ast.Call,
            ):
                continue

            sink_name = self._call_name(
                ast_node
            )

            if sink_name not in sink_names:
                continue

            sink_line = getattr(
                ast_node,
                "lineno",
                0,
            )

            for argument in ast_node.args:

                origin = self._expression_taint(
                    argument,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                if origin is None:
                    continue

                variable = self._tainted_variable(
                    argument,
                    tainted,
                )

                if variable is None:
                    variable = self._expression_label(
                        argument
                    )

                definition_id = (
                    self._definition_id_for_variable(
                        variable,
                        sink_line,
                        data_flow,
                        definition_ids,
                    )
                )

                use_id = self._use_id_for_sink(
                    variable,
                    sink_line,
                    def_use,
                )

                finding = TaintFlowFinding(
                    source_name=origin.source_name,
                    source_line=origin.source_line,
                    sink_name=sink_name,
                    sink_line=sink_line,
                    variable=variable,
                    definition_id=definition_id,
                    use_id=use_id,
                    path=(
                        origin.source_name,
                        variable,
                        sink_name,
                    ),
                )

                result.findings.append(
                    finding
                )

                vulnerability = (
                    self.vulnerability_engine.analyze_flow(
                        source_name=origin.source_name,
                        source_line=origin.source_line,
                        sink_name=sink_name,
                        sink_line=sink_line,
                        variable=variable,
                        definition_id=definition_id,
                        use_id=use_id,
                        path=finding.path,
                    )
                )

                if vulnerability is not None:
                    result.vulnerabilities.append(
                        vulnerability
                    )

    # ============================================================
    # INTERPROCEDURAL EXECUTION
    # ============================================================

    def _execute_interprocedural(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        tainted: dict[str, _TaintOrigin],
        function_by_name: dict[
            str,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ],
        source_names: set[str],
        sanitizer_names: set[str],
        sink_names: set[str],
        result: TaintAnalysisResult,
        summaries: dict[str, bool],
        call_stack: tuple[str, ...] = (),
    ) -> Optional[_TaintOrigin]:

        if function_node.name in call_stack:
            return None

        current_stack = (
            *call_stack,
            function_node.name,
        )

        function_id = self._node_ids.get(id(function_node))

        if function_id:
            self._function_stack.append(function_id)

        self._node_stack.append(id(function_node))
        self._argv_frames.append(set())

        try:
            return self._exec_block(
                function_node.body,
                tainted,
                function_by_name,
                source_names,
                sanitizer_names,
                sink_names,
                result,
                summaries,
                current_stack,
            )
        finally:
            self._argv_frames.pop()
            self._node_stack.pop()

            if function_id:
                self._function_stack.pop()

    # ------------------------------------------------------------
    # Return-value summaries (symbolic execution of the callee)
    # ------------------------------------------------------------

    def _note_return(self, value, origin, taint_of) -> None:
        if not self._node_stack:
            return

        node_id = self._node_stack[-1]
        scalar, elements = self._return_shapes.get(node_id, (None, None))

        if scalar is None and origin is not None:
            scalar = origin

        if isinstance(value, ast.Tuple):
            current = [taint_of(element) for element in value.elts]

            if elements is None or len(elements) != len(current):
                elements = current
            else:
                elements = [
                    first if first is not None else second
                    for first, second in zip(elements, current)
                ]

        self._return_shapes[node_id] = (scalar, elements)

    def _map_call_arguments(
        self,
        call: ast.Call,
        callee: ast.FunctionDef | ast.AsyncFunctionDef,
        tainted: dict[str, _TaintOrigin],
        function_by_name,
        source_names,
        sanitizer_names,
        summaries,
        call_stack,
    ) -> dict[str, _TaintOrigin]:
        """Taint state of the callee's parameters for this call."""

        parameters = [
            argument.arg
            for argument in (*callee.args.posonlyargs, *callee.args.args)
        ]

        offset = (
            1
            if (
                isinstance(call.func, ast.Attribute)
                and parameters
                and parameters[0] in {"self", "cls"}
            )
            else 0
        )

        mapped: list[tuple[str, ast.AST]] = []

        for index, argument in enumerate(call.args):
            if index + offset >= len(parameters):
                break

            mapped.append((parameters[index + offset], argument))

        keyword_parameters = {
            *parameters,
            *(argument.arg for argument in callee.args.kwonlyargs),
        }

        for keyword in call.keywords:
            if keyword.arg in keyword_parameters:
                mapped.append((keyword.arg, keyword.value))

        state: dict[str, _TaintOrigin] = {}

        for parameter, argument in mapped:
            origin = self._expression_taint_interprocedural(
                argument, tainted, function_by_name, source_names,
                sanitizer_names, summaries, call_stack,
            )

            if origin is not None:
                state[parameter] = origin

        return state

    def _call_return_shape(
        self,
        call: ast.Call,
        callee: ast.FunctionDef | ast.AsyncFunctionDef,
        tainted: dict[str, _TaintOrigin],
        function_by_name,
        source_names,
        sanitizer_names,
        summaries,
        call_stack,
    ) -> tuple:
        """(scalar origin, per-element origins) of what `callee` returns."""

        state = self._map_call_arguments(
            call, callee, tainted, function_by_name, source_names,
            sanitizer_names, summaries, call_stack,
        )

        key = (
            id(callee),
            tuple(sorted(
                (
                    name,
                    origin.source_name,
                    origin.source_line,
                    tuple(sorted(origin.neutralized)),
                )
                for name, origin in state.items()
            )),
        )

        if key in self._return_cache:
            return self._return_cache[key]

        self._return_cache[key] = (None, None)  # breaks recursion cycles
        self._return_shapes.pop(id(callee), None)

        self._execute_interprocedural(
            function_node=callee,
            tainted=dict(state),
            function_by_name=function_by_name,
            source_names=source_names,
            sanitizer_names=sanitizer_names,
            sink_names=self._sink_names,
            result=TaintAnalysisResult(function_name="<summary>"),
            summaries=summaries,
            call_stack=call_stack,
        )

        shape = self._return_shapes.pop(id(callee), (None, None))
        self._return_cache[key] = shape

        return shape

    PATH_NEUTRAL_CALLS = frozenset({"basename", "secure_filename", "get_valid_filename"})
    PATH_NEUTRAL_ATTRS = frozenset({"suffix", "suffixes", "stem"})

    @staticmethod
    def _neutralize(origin, *rule_ids):
        if origin is None:
            return None

        return _TaintOrigin(
            source_name=origin.source_name,
            source_line=origin.source_line,
            neutralized=origin.neutralized | frozenset(rule_ids),
        )

    @staticmethod
    def _pick(origins):
        """First fully-tainted origin, else the first neutralised one."""

        fallback = None

        for origin in origins:
            if origin is None:
                continue

            if not origin.neutralized:
                return origin

            if fallback is None:
                fallback = origin

        return fallback

    def _value_elements(
        self,
        value: ast.AST,
        tainted,
        function_by_name,
        source_names,
        sanitizer_names,
        summaries,
        call_stack,
        taint_of,
    ):
        """Per-element taint of a tuple literal or a call returning a tuple."""

        if isinstance(value, (ast.Tuple, ast.List)):
            return [taint_of(element) for element in value.elts]

        if isinstance(value, ast.Call):
            callee = self._resolve_callee(value, function_by_name)

            if callee is not None and callee.name not in call_stack:
                _, elements = self._call_return_shape(
                    value, callee, tainted, function_by_name, source_names,
                    sanitizer_names, summaries, call_stack,
                )

                return elements

        return None

    def _resolve_callee(self, call: ast.Call, function_by_name):
        """Project function a call refers to (None for library calls)."""

        callee = function_by_name.get(self._call_name(call))

        if callee is None:
            return None

        if isinstance(call.func, ast.Attribute):
            root, _ = catalog._chain(call.func.value)

            if root in catalog.EXTERNAL_MODULES:
                return None

        return callee

    _MUTATORS = frozenset({
        "append", "extend", "add", "insert", "update", "setdefault", "appendleft",
    })

    def _exec_block(
        self,
        statements: list[ast.stmt],
        tainted: dict[str, _TaintOrigin],
        function_by_name: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
        source_names: set[str],
        sanitizer_names: set[str],
        sink_names: set[str],
        result: TaintAnalysisResult,
        summaries: dict[str, bool],
        call_stack: tuple[str, ...],
    ) -> Optional[_TaintOrigin]:
        """Walk every statement kind (if/for/while/with/try/match included)."""

        return_origin: Optional[_TaintOrigin] = None

        def taint_of(expression):
            return self._expression_taint_interprocedural(
                expression, tainted, function_by_name, source_names,
                sanitizer_names, summaries, call_stack,
            )

        def check(expression):
            if expression is not None:
                self._check_interprocedural_sinks(
                    expression, tainted, function_by_name, source_names,
                    sanitizer_names, sink_names, result, summaries, call_stack,
                )

        def run(block, state):
            return self._exec_block(
                block, state, function_by_name, source_names, sanitizer_names,
                sink_names, result, summaries, call_stack,
            )

        def branch(block):
            state = dict(tainted)
            returned = run(block, state)
            return state, returned

        def merge(*states):
            for state in states:
                for name, origin in state.items():
                    tainted.setdefault(name, origin)

        for statement in statements:

            if isinstance(statement, ast.Return):
                if statement.value is not None:
                    check(statement.value)
                    origin = taint_of(statement.value)
                    self._note_return(statement.value, origin, taint_of)
                    if origin is not None:
                        return_origin = origin
                break

            if isinstance(statement, ast.Assign):
                check(statement.value)
                origin = taint_of(statement.value)
                elements = self._value_elements(
                    statement.value, tainted, function_by_name, source_names,
                    sanitizer_names, summaries, call_stack, taint_of,
                )
                for target in statement.targets:
                    if (
                        elements is not None
                        and isinstance(target, (ast.Tuple, ast.List))
                        and len(target.elts) == len(elements)
                        and not any(isinstance(t, ast.Starred) for t in target.elts)
                    ):
                        for sub_target, sub_origin in zip(target.elts, elements):
                            self._assign_taint(sub_target, sub_origin, tainted)
                    else:
                        self._assign_taint(target, origin, tainted)

                    if isinstance(target, ast.Name) and self._argv_frames:
                        argv = catalog.argv_list(statement.value)

                        if argv:
                            self._argv_frames[-1].add(target.id)
                        else:
                            self._argv_frames[-1].discard(target.id)
                continue

            if isinstance(statement, ast.AnnAssign):
                if statement.value is not None:
                    check(statement.value)
                    self._assign_taint(
                        statement.target, taint_of(statement.value), tainted,
                    )
                continue

            if isinstance(statement, ast.AugAssign):
                check(statement.value)
                existing = (
                    tainted.get(statement.target.id)
                    if isinstance(statement.target, ast.Name) else None
                )
                origin = existing if existing is not None else taint_of(statement.value)
                self._assign_taint(statement.target, origin, tainted)
                continue

            if isinstance(statement, ast.Expr):
                check(statement.value)
                call = statement.value
                if isinstance(call, ast.Await):
                    call = call.value
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr in self._MUTATORS
                ):
                    root, _ = catalog._chain(call.func.value)
                    if root is not None:
                        for argument in call.args:
                            origin = taint_of(argument)
                            if origin is not None:
                                tainted.setdefault(root, origin)
                continue

            if isinstance(statement, ast.If):
                check(statement.test)
                body_state, body_ret = branch(statement.body)
                else_state, else_ret = branch(statement.orelse)
                merge(body_state, else_state)
                for returned in (body_ret, else_ret):
                    if returned is not None:
                        return_origin = returned
                continue

            if isinstance(statement, (ast.For, ast.AsyncFor)):
                check(statement.iter)
                state = dict(tainted)
                self._assign_taint(statement.target, taint_of(statement.iter), state)
                returned = run(statement.body, state)
                else_state, else_ret = branch(statement.orelse)
                merge(state, else_state)
                for r in (returned, else_ret):
                    if r is not None:
                        return_origin = r
                continue

            if isinstance(statement, ast.While):
                check(statement.test)
                body_state, body_ret = branch(statement.body)
                else_state, else_ret = branch(statement.orelse)
                merge(body_state, else_state)
                for r in (body_ret, else_ret):
                    if r is not None:
                        return_origin = r
                continue

            if isinstance(statement, (ast.With, ast.AsyncWith)):
                for item in statement.items:
                    check(item.context_expr)
                    if item.optional_vars is not None:
                        self._assign_taint(
                            item.optional_vars, taint_of(item.context_expr), tainted,
                        )
                returned = run(statement.body, tainted)
                if returned is not None:
                    return_origin = returned
                continue

            try_types = tuple(
                t for t in (ast.Try, getattr(ast, "TryStar", None)) if t is not None
            )
            if isinstance(statement, try_types):
                states = []
                returns = []
                for block in (
                    statement.body,
                    *[handler.body for handler in statement.handlers],
                    statement.orelse,
                ):
                    state, returned = branch(block)
                    states.append(state)
                    returns.append(returned)
                merge(*states)
                returns.append(run(statement.finalbody, tainted))
                for r in returns:
                    if r is not None:
                        return_origin = r
                continue

            match_type = getattr(ast, "Match", None)
            if match_type is not None and isinstance(statement, match_type):
                check(statement.subject)
                states = []
                for case in statement.cases:
                    state, returned = branch(case.body)
                    states.append(state)
                    if returned is not None:
                        return_origin = returned
                merge(*states)
                continue

        return return_origin

    # ============================================================
    # INTERPROCEDURAL EXPRESSION
    # ============================================================

    def _expression_taint_interprocedural(
        self,
        node: ast.AST,
        tainted: dict[str, _TaintOrigin],
        function_by_name: dict[
            str,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ],
        source_names: set[str],
        sanitizer_names: set[str],
        summaries: dict[str, bool],
        call_stack: tuple[str, ...],
    ) -> Optional[_TaintOrigin]:

        if isinstance(
            node,
            ast.Name,
        ):
            return tainted.get(
                node.id
            )

        if isinstance(node, (ast.Attribute, ast.Subscript)):
            attribute_source = catalog.expression_source(node)

            if attribute_source is not None:
                return _TaintOrigin(
                    source_name=attribute_source,
                    source_line=getattr(node, "lineno", 0),
                )

        if isinstance(node, ast.Attribute) and node.attr in self.PATH_NEUTRAL_ATTRS:
            return self._neutralize(
                self._expression_taint_interprocedural(
                    node.value, tainted, function_by_name, source_names,
                    sanitizer_names, summaries, call_stack,
                ),
                "PATH_TRAVERSAL",
            )

        if isinstance(
            node,
            ast.Call,
        ):

            call_name = self._call_name(
                node
            )

            # Sanitizer.
            if call_name in sanitizer_names:
                return None

            if call_name in self.PATH_NEUTRAL_CALLS:
                return self._neutralize(
                    self._pick(
                        self._expression_taint_interprocedural(
                            a, tainted, function_by_name, source_names,
                            sanitizer_names, summaries, call_stack,
                        )
                        for a in node.args
                    ),
                    "PATH_TRAVERSAL",
                )

            # Direct source.
            source_origin = (
                self._source_origin_from_call(
                    node,
                    source_names,
                )
            )

            if source_origin is not None:
                return source_origin

            # Known project function: what does it actually return?
            callee = self._resolve_callee(
                node,
                function_by_name,
            )

            if callee is not None and callee.name not in call_stack:

                scalar, _ = self._call_return_shape(
                    node,
                    callee,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    summaries,
                    call_stack,
                )

                return scalar

            # Unknown call: inspect arguments.
            for argument in node.args:
                origin = (
                    self._expression_taint_interprocedural(
                        argument,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        summaries,
                        call_stack,
                    )
                )

                if origin is not None:
                    return origin

            for keyword in node.keywords:
                origin = (
                    self._expression_taint_interprocedural(
                        keyword.value,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        summaries,
                        call_stack,
                    )
                )

                if origin is not None:
                    return origin

            # Method receivers: name.strip(), query.format(...)
            if isinstance(node.func, ast.Attribute):
                origin = (
                    self._expression_taint_interprocedural(
                        node.func.value,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        summaries,
                        call_stack,
                    )
                )

                if origin is not None:
                    return origin

            return None

        return self._pick(
            self._expression_taint_interprocedural(
                child,
                tainted,
                function_by_name,
                source_names,
                sanitizer_names,
                summaries,
                call_stack,
            )
            for child in ast.iter_child_nodes(node)
        )

    # ============================================================
    # INTERPROCEDURAL SINKS
    # ============================================================

    def _check_interprocedural_sinks(
        self,
        node: ast.AST,
        tainted: dict[str, _TaintOrigin],
        function_by_name: dict[
            str,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ],
        source_names: set[str],
        sanitizer_names: set[str],
        sink_names: set[str],
        result: TaintAnalysisResult,
        summaries: dict[str, bool],
        call_stack: tuple[str, ...],
    ) -> None:

        for ast_node in ast.walk(node):

            if not isinstance(
                ast_node,
                ast.Call,
            ):
                continue

            sink_name = self._call_name(
                ast_node
            )

            # ----------------------------------------------------
            # Direct sink.
            # ----------------------------------------------------

            resolved = self._resolve_sink(
                ast_node,
                sink_names,
            )

            if resolved is not None:

                canonical_sink, sink_arguments, sink_rule = resolved

                for argument in sink_arguments:

                    origin = (
                        self._expression_taint_interprocedural(
                            argument,
                            tainted,
                            function_by_name,
                            source_names,
                            sanitizer_names,
                            summaries,
                            call_stack,
                        )
                    )

                    if origin is None:
                        continue

                    variable = self._tainted_variable(
                        argument,
                        tainted,
                    )

                    if variable is None:
                        variable = self._expression_label(
                            argument
                        )

                    if sink_rule in origin.neutralized:
                        continue

                    self._record_flow(
                        result,
                        origin,
                        canonical_sink,
                        getattr(ast_node, "lineno", 0),
                        variable,
                    )

                continue

            # ----------------------------------------------------
            # Project function call.
            # ----------------------------------------------------

            callee = self._resolve_callee(
                ast_node,
                function_by_name,
            )

            if callee is None:
                continue

            if callee.name in call_stack:
                continue

            # Run the callee once with every tainted parameter.
            state = self._map_call_arguments(
                ast_node,
                callee,
                tainted,
                function_by_name,
                source_names,
                sanitizer_names,
                summaries,
                call_stack,
            )

            if not state:
                continue

            self._execute_interprocedural(
                function_node=callee,
                tainted=state,
                function_by_name=function_by_name,
                source_names=source_names,
                sanitizer_names=sanitizer_names,
                sink_names=sink_names,
                result=result,
                summaries=summaries,
                call_stack=call_stack,
            )

    # ============================================================
    # SINK RESOLUTION / FINDING RECORDING
    # ============================================================

    def _resolve_sink(
        self,
        call: ast.Call,
        sink_names: set[str],
    ) -> Optional[tuple[str, list[ast.AST], Optional[str]]]:
        """Return (canonical sink name, argument nodes that matter, rule id)."""

        if self._use_catalog_sinks:
            match = catalog.match_sink(call)

            if match is not None:
                spec, canonical = match

                first = call.args[0] if call.args else None

                if (
                    spec.shell_sensitive
                    and isinstance(first, ast.Name)
                    and self._argv_frames
                    and first.id in self._argv_frames[-1]
                    and not catalog.has_shell_true(call)
                ):
                    # cmd = ["git", ...]; subprocess.run(cmd)  -> no shell
                    return None

                return (
                    canonical,
                    catalog.sink_arguments(call, spec),
                    spec.rule_id,
                )

        name = self._call_name(call)

        if name in sink_names:
            return name, [
                *call.args,
                *(keyword.value for keyword in call.keywords),
            ], None

        return None

    def _record_flow(
        self,
        result: TaintAnalysisResult,
        origin: _TaintOrigin,
        sink_name: str,
        sink_line: int,
        variable: str,
    ) -> None:

        function_id = (
            self._function_stack[-1]
            if self._function_stack
            else ""
        )

        file_path = function_id.partition("::")[0] if function_id else ""
        function_name = function_id.rpartition("::")[2] if function_id else ""

        finding = TaintFlowFinding(
            source_name=origin.source_name,
            source_line=origin.source_line,
            sink_name=sink_name,
            sink_line=sink_line,
            variable=variable,
            path=(
                origin.source_name,
                variable,
                sink_name,
            ),
            file=file_path,
            function=function_name,
            function_id=function_id,
        )

        result.findings.append(finding)

        vulnerability = self.vulnerability_engine.analyze_flow(
            source_name=origin.source_name,
            source_line=origin.source_line,
            sink_name=sink_name,
            sink_line=sink_line,
            variable=variable,
            path=finding.path,
            file=file_path,
            function=function_name,
            function_id=function_id,
        )

        if vulnerability is not None:
            result.vulnerabilities.append(vulnerability)

    @staticmethod
    def _dedupe(result: TaintAnalysisResult) -> None:
        """One finding per sink location (same sink reached by several paths)."""

        seen: set[tuple] = set()
        findings = []

        for finding in result.findings:
            key = (finding.function_id, finding.sink_name, finding.sink_line)

            if key not in seen:
                seen.add(key)
                findings.append(finding)

        seen_vulns: set[tuple] = set()
        vulnerabilities = []

        for vulnerability in result.vulnerabilities:
            key = (
                vulnerability.function_id,
                vulnerability.rule_id,
                vulnerability.sink_name,
                vulnerability.sink_line,
            )

            if key not in seen_vulns:
                seen_vulns.add(key)
                vulnerabilities.append(vulnerability)

        result.findings = findings
        result.vulnerabilities = vulnerabilities

    # ============================================================
    # FUNCTION SUMMARY
    # ============================================================

    def _function_returns_taint(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_names: set[str],
        sanitizer_names: set[str],
    ) -> bool:
        """
        Determine whether a function can return tainted data.

        This is intentionally conservative.
        """

        tainted_parameters = {
            argument.arg
            for argument in function_node.args.args
        }

        for node in ast.walk(function_node):

            if not isinstance(
                node,
                ast.Return,
            ):
                continue

            if node.value is None:
                continue

            if self._expression_contains_source(
                node.value,
                source_names,
            ):
                return True

            if self._expression_contains_name(
                node.value,
                tainted_parameters,
                sanitizer_names,
            ):
                return True

        return False

    # ============================================================
    # AST DISCOVERY
    # ============================================================

    @staticmethod
    def _find_sources(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_names: set[str],
    ) -> list[TaintSource]:

        sources: list[TaintSource] = []

        for node in TaintAnalyzer._walk_function(function_node):
            if not isinstance(node, ast.Call):
                continue

            name = TaintAnalyzer._source_name_for_call(
                node,
                source_names,
            )

            if name is None:
                continue

            sources.append(
                TaintSource(
                    name=name,
                    line=getattr(node, "lineno", 0),
                )
            )

        return sources

    @staticmethod
    def _find_sanitizers(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        sanitizer_names: set[str],
    ) -> list[TaintSanitizer]:

        sanitizers = []

        for node in TaintAnalyzer._walk_function(
            function_node
        ):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = TaintAnalyzer._call_name(
                node
            )

            if name in sanitizer_names:
                sanitizers.append(
                    TaintSanitizer(
                        name=name,
                        line=getattr(
                            node,
                            "lineno",
                            0,
                        ),
                    )
                )

        return sanitizers

    @staticmethod
    def _find_sinks(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        sink_names: set[str],
    ) -> list[TaintSink]:

        sinks = []

        for node in TaintAnalyzer._walk_function(
            function_node
        ):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = TaintAnalyzer._call_name(
                node
            )

            if name in sink_names:
                sinks.append(
                    TaintSink(
                        name=name,
                        line=getattr(
                            node,
                            "lineno",
                            0,
                        ),
                    )
                )

        return sinks

    
    @staticmethod
    def _is_request_source(node: ast.Call) -> bool:
        """Recognize common web-framework request inputs."""

        if not isinstance(node.func, ast.Attribute):
            return False

        method = node.func.attr

        # request.GET.get(...), request.POST.get(...), etc.
        if method == "get":
            receiver = node.func.value

            if not isinstance(receiver, ast.Attribute):
                return False

            if receiver.attr not in {
                "GET",
                "POST",
                "headers",
                "query_params",
                "cookies",
            }:
                return False

            request_object = receiver.value

            return (
                isinstance(request_object, ast.Name)
                and request_object.id in {"request", "req"}
            )

        # request.json() and request.get_json()
        if method in {"json", "get_json"}:
            receiver = node.func.value

            return (
                isinstance(receiver, ast.Name)
                and receiver.id in {"request", "req"}
            )

        return False

    @staticmethod
    def _source_name_for_call(
        node: ast.Call,
        source_names: set[str],
    ) -> Optional[str]:
        """Resolve a call to a recognized taint source."""

        catalog_source = catalog.expression_source(node)

        if catalog_source is not None:
            return catalog_source

        call_name = TaintAnalyzer._call_name(node)

        if call_name in source_names:
            return call_name

        if TaintAnalyzer._is_request_source(node):
            return "request"

        return None
    
    
    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _call_name(
        node: ast.Call,
    ) -> str:

        if isinstance(
            node.func,
            ast.Name,
        ):
            return node.func.id

        if isinstance(
            node.func,
            ast.Attribute,
        ):
            return node.func.attr

        return ""

    @staticmethod
    def _walk_function(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ):
        stack = list(
            reversed(
                function_node.body
            )
        )

        while stack:

            node = stack.pop()

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                    ast.Lambda,
                ),
            ):
                continue

            yield node

            stack.extend(
                reversed(
                    list(
                        ast.iter_child_nodes(node)
                    )
                )
            )

    @staticmethod
    def _function_name(
        function_id: str,
    ) -> str:

        if "::" in function_id:
            return function_id.rsplit(
                "::",
                1,
            )[-1]

        return function_id

    @staticmethod
    def _tainted_variable(
        node: ast.AST,
        tainted: dict[str, _TaintOrigin],
    ) -> Optional[str]:

        if isinstance(
            node,
            ast.Name,
        ):
            if node.id in tainted:
                return node.id

        for child in ast.iter_child_nodes(node):

            variable = (
                TaintAnalyzer._tainted_variable(
                    child,
                    tainted,
                )
            )

            if variable is not None:
                return variable

        return None

    @staticmethod
    def _expression_label(
        node: ast.AST,
    ) -> str:

        if isinstance(
            node,
            ast.Call,
        ):
            name = TaintAnalyzer._call_name(
                node
            )

            if name:
                return f"{name}(...)"

        return "<tainted-expression>"

    @staticmethod
    def _build_definition_id_map(
        data_flow: DataFlowResult,
    ) -> dict[tuple[str, int], str]:

        result = {}

        for index, definition in enumerate(
            data_flow.definitions
        ):
            result.setdefault(
                (
                    definition.name,
                    definition.line,
                ),
                f"D{index}",
            )

        return result

    @staticmethod
    def _definition_id_for_variable(
        variable: str,
        sink_line: int,
        data_flow: DataFlowResult,
        definition_ids: dict[
            tuple[str, int],
            str,
        ],
    ) -> str:

        candidates = []

        for definition in data_flow.definitions:

            if definition.name != variable:
                continue

            if definition.line > sink_line:
                continue

            definition_id = definition_ids.get(
                (
                    definition.name,
                    definition.line,
                )
            )

            if definition_id is not None:
                candidates.append(
                    (
                        definition.line,
                        definition_id,
                    )
                )

        if not candidates:
            return ""

        candidates.sort(
            key=lambda item: item[0]
        )

        return candidates[-1][1]

    @staticmethod
    def _use_id_for_sink(
        variable: str,
        sink_line: int,
        def_use: DefUseResult,
    ) -> str:

        for chain in def_use.chains:

            if (
                chain.variable == variable
                and chain.use_line == sink_line
            ):
                return chain.use_id

        return ""

    @staticmethod
    def _expression_contains_source(
        node: ast.AST,
        source_names: set[str],
    ) -> bool:

        for child in ast.walk(node):

            if not isinstance(
                child,
                ast.Call,
            ):
                continue

            if (
                TaintAnalyzer._call_name(child)
                in source_names
            ):
                return True

        return False

    @staticmethod
    def _expression_contains_name(
        node: ast.AST,
        names: set[str],
        sanitizer_names: set[str],
    ) -> bool:

        if isinstance(
            node,
            ast.Call,
        ):
            if (
                TaintAnalyzer._call_name(node)
                in sanitizer_names
            ):
                return False

        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Name,
            ) and child.id in names:
                return True

        return False

    @staticmethod
    def _temporary_block_function(
        original: ast.FunctionDef | ast.AsyncFunctionDef,
        body: list[ast.stmt],
    ) -> ast.FunctionDef:

        return ast.FunctionDef(
            name=f"{original.name}.__block__",
            args=original.args,
            body=body,
            decorator_list=[],
            returns=original.returns,
        )