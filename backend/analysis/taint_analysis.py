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

        for function_name, function_node in (
            function_by_name.items()
        ):

            state: dict[str, _TaintOrigin] = {}

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
        # Direct variable.
        if isinstance(node, ast.Name):
            return tainted.get(node.id)

        # Sanitizer call removes taint.
           # Call expression.
        if isinstance(node, ast.Call):
            # Direct source call.
            call_name = self._call_name(node)

            if call_name in source_names:
                return _TaintOrigin(
                    source_name=call_name,
                    source_line=getattr(node, "lineno", 0),
                )

            # Sanitizer call removes taint.
            if call_name in sanitizer_names:
                return None

            # Propagate taint through normal call arguments.
            for arg in node.args:
                arg_origin = self._expression_taint(
                    arg,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                if arg_origin is not None:
                    return arg_origin

            # Propagate taint through method calls.
            #
            # Examples:
            #   user_input.strip()
            #   user_input.lower()
            #   user_input.encode()
            #
            # The tainted value is the method receiver:
            #   user_input
            #
            # which is stored in node.func.value.
            if isinstance(node.func, ast.Attribute):
                receiver_origin = self._expression_taint(
                    node.func.value,
                    tainted,
                    source_names,
                    sanitizer_names,
                )

                if receiver_origin is not None:
                    return receiver_origin

            return None
        # Recursively inspect expressions.
        for child in ast.iter_child_nodes(node):

            origin = self._expression_taint(
                child,
                tainted,
                source_names,
                sanitizer_names,
            )

            if origin is not None:
                return origin

        return None

    # ============================================================
    # SOURCE
    # ============================================================

    @staticmethod
    def _source_origin_from_call(
        node: ast.AST,
        source_names: set[str],
    ) -> Optional[_TaintOrigin]:

        if not isinstance(node, ast.Call):
            return None

        name = TaintAnalyzer._call_name(node)

        if name not in source_names:
            return None

        return _TaintOrigin(
            source_name=name,
            source_line=getattr(
                node,
                "lineno",
                0,
            ),
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

        return_origin: Optional[_TaintOrigin] = None

        for statement in function_node.body:

            # ----------------------------------------------------
            # RETURN
            # ----------------------------------------------------

            if isinstance(
                statement,
                ast.Return,
            ):

                if statement.value is None:
                    return return_origin

                return_origin = self._expression_taint_interprocedural(
                    statement.value,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    summaries,
                    current_stack,
                )

                continue

            # ----------------------------------------------------
            # ASSIGNMENT
            # ----------------------------------------------------

            if isinstance(
                statement,
                ast.Assign,
            ):

                origin = self._expression_taint_interprocedural(
                    statement.value,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    summaries,
                    current_stack,
                )

                for target in statement.targets:
                    self._assign_taint(
                        target,
                        origin,
                        tainted,
                    )

                self._check_interprocedural_sinks(
                    statement.value,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    summaries,
                    current_stack,
                )

                continue

            # ----------------------------------------------------
            # EXPRESSION / CALL
            # ----------------------------------------------------

            if isinstance(
                statement,
                ast.Expr,
            ):

                self._check_interprocedural_sinks(
                    statement.value,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    summaries,
                    current_stack,
                )

                continue

            # ----------------------------------------------------
            # IF
            # ----------------------------------------------------

            if isinstance(
                statement,
                ast.If,
            ):

                self._execute_interprocedural(
                    function_node=self._temporary_block_function(
                        function_node,
                        statement.body,
                    ),
                    tainted=tainted,
                    function_by_name=function_by_name,
                    source_names=source_names,
                    sanitizer_names=sanitizer_names,
                    sink_names=sink_names,
                    result=result,
                    summaries=summaries,
                    call_stack=current_stack,
                )

                self._execute_interprocedural(
                    function_node=self._temporary_block_function(
                        function_node,
                        statement.orelse,
                    ),
                    tainted=tainted,
                    function_by_name=function_by_name,
                    source_names=source_names,
                    sanitizer_names=sanitizer_names,
                    sink_names=sink_names,
                    result=result,
                    summaries=summaries,
                    call_stack=current_stack,
                )

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

            # Direct source.
            source_origin = (
                self._source_origin_from_call(
                    node,
                    source_names,
                )
            )

            if source_origin is not None:
                return source_origin

            # Known project function.
            callee = function_by_name.get(
                call_name
            )

            if (
                callee is not None
                and summaries.get(
                    call_name,
                    False,
                )
            ):

                argument_origins = [
                    self._expression_taint_interprocedural(
                        argument,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        summaries,
                        call_stack,
                    )
                    for argument in node.args
                ]

                for origin in argument_origins:
                    if origin is not None:
                        return origin

                # The callee itself may contain a source.
                source_nodes = self._find_sources(
                    callee,
                    source_names,
                )

                if source_nodes:
                    source = source_nodes[0]

                    return _TaintOrigin(
                        source_name=source.name,
                        source_line=source.line,
                    )

                return None

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

            return None

        for child in ast.iter_child_nodes(node):

            origin = (
                self._expression_taint_interprocedural(
                    child,
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

            if sink_name in sink_names:

                for argument in ast_node.args:

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

                    sink_line = getattr(
                        ast_node,
                        "lineno",
                        0,
                    )

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
                            path=finding.path,
                        )
                    )

                    if vulnerability is not None:
                        result.vulnerabilities.append(
                            vulnerability
                        )

                continue

            # ----------------------------------------------------
            # Project function call.
            # ----------------------------------------------------

            callee = function_by_name.get(
                sink_name
            )

            if callee is None:
                continue

            if callee.name in call_stack:
                continue

            # Map tainted caller arguments to callee parameters.
            for index, argument in enumerate(
                ast_node.args
            ):

                if index >= len(
                    callee.args.args
                ):
                    break

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

                parameter = callee.args.args[
                    index
                ].arg

                callee_state = {
                    parameter: origin
                }

                self._execute_interprocedural(
                    function_node=callee,
                    tainted=callee_state,
                    function_by_name=function_by_name,
                    source_names=source_names,
                    sanitizer_names=sanitizer_names,
                    sink_names=sink_names,
                    result=result,
                    summaries=summaries,
                    call_stack=call_stack,
                )

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

        sources = []

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

            if name in source_names:
                sources.append(
                    TaintSource(
                        name=name,
                        line=getattr(
                            node,
                            "lineno",
                            0,
                        ),
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