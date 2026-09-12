"""
Taint Analysis - Milestone 2.

Detects propagation of potentially untrusted data from configured
sources to configured sinks.

Supported propagation in this milestone:

    source() -> variable
    variable -> variable
    variable -> expression
    expression containing variable -> sink

Example:

    user_input = request_input()
    query = user_input
    execute(query)

Flow:

    request_input
          |
          v
      user_input
          |
          v
         query
          |
          v
       execute
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from backend.analysis.data_flow import DataFlowResult
from backend.analysis.def_use import DefUseResult


# ================================================================
# SOURCE
# ================================================================


@dataclass(frozen=True)
class TaintSource:
    """Represents a configured source of potentially untrusted data."""

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
# SINK
# ================================================================


@dataclass(frozen=True)
class TaintSink:
    """Represents a configured sensitive sink."""

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
# FINDING
# ================================================================


@dataclass(frozen=True)
class TaintFlowFinding:
    """Represents one tainted flow from source to sink."""

    source_name: str
    source_line: int

    sink_name: str
    sink_line: int

    variable: str

    definition_id: str
    use_id: str

    path: tuple[str, ...] = field(
        default_factory=tuple
    )

    reason: str = (
        "Potentially tainted data flows from a source to a sensitive sink."
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
    """Complete taint-analysis result for one function."""

    function_name: str

    sources: list[TaintSource] = field(
        default_factory=list
    )

    sinks: list[TaintSink] = field(
        default_factory=list
    )

    findings: list[TaintFlowFinding] = field(
        default_factory=list
    )

    @property
    def finding_count(self) -> int:
        return len(self.findings)

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
            "sinks": [
                sink.to_dict()
                for sink in self.sinks
            ],
            "finding_count": self.finding_count,
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
        }


# ================================================================
# TAINT STATE
# ================================================================


@dataclass(frozen=True)
class _TaintOrigin:
    """
    Internal representation of where taint originated.
    """

    source_name: str
    source_line: int


# ================================================================
# ANALYZER
# ================================================================


class TaintAnalyzer:
    """
    Performs intra-procedural taint analysis.

    Milestone 2 supports:

        source() -> x
        x -> y
        y -> expression
        expression -> sink()

    The analysis is intentionally conservative.

    If an expression contains a tainted variable, the expression
    is considered tainted.

    Example:

        user_input = request_input()

        query = "SELECT " + user_input

        execute(query)

    The value of query is considered tainted.
    """

    DEFAULT_SOURCE_NAMES = {
        "input",
        "request_input",
        "get_user_input",
    }

    DEFAULT_SINK_NAMES = {
        "execute",
        "execute_query",
        "run_command",
    }

    def analyze(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        data_flow: DataFlowResult,
        def_use: DefUseResult,
        source_names: Optional[Iterable[str]] = None,
        sink_names: Optional[Iterable[str]] = None,
    ) -> TaintAnalysisResult:
        """
        Analyze one function for tainted source-to-sink flows.
        """

        source_names_set = set(
            source_names
            if source_names is not None
            else self.DEFAULT_SOURCE_NAMES
        )

        sink_names_set = set(
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

        # --------------------------------------------------------
        # Discover configured sources and sinks.
        # --------------------------------------------------------

        result.sources = self._find_sources(
            function_node,
            source_names_set,
        )

        result.sinks = self._find_sinks(
            function_node,
            sink_names_set,
        )

        if not result.sources or not result.sinks:
            return result

        # --------------------------------------------------------
        # Build lookup tables for existing Def-Use information.
        # --------------------------------------------------------

        definition_ids = self._build_definition_id_map(
            data_flow
        )

        # --------------------------------------------------------
        # Walk the function and propagate taint.
        # --------------------------------------------------------

        tainted: dict[str, _TaintOrigin] = {}

        self._analyze_statements(
            statements=function_node.body,
            tainted=tainted,
            source_names=source_names_set,
            sink_names=sink_names_set,
            result=result,
            data_flow=data_flow,
            def_use=def_use,
            definition_ids=definition_ids,
        )

        return result

    # ============================================================
    # STATEMENT ANALYSIS
    # ============================================================

    def _analyze_statements(
        self,
        statements: list[ast.stmt],
        tainted: dict[str, _TaintOrigin],
        source_names: set[str],
        sink_names: set[str],
        result: TaintAnalysisResult,
        data_flow: DataFlowResult,
        def_use: DefUseResult,
        definition_ids: dict[tuple[str, int], str],
    ) -> None:
        """
        Analyze statements in source order.

        Branches and loops are handled conservatively by propagating
        taint discovered inside their bodies back to the surrounding
        state.
        """

        for statement in statements:

            # ----------------------------------------------------
            # ASSIGNMENT
            # ----------------------------------------------------

            if isinstance(statement, ast.Assign):

                value_taint = self._expression_taint(
                    statement.value,
                    tainted,
                    source_names,
                )

                # A direct source call creates taint even when the
                # expression does not contain a previously tainted
                # variable.
                source_origin = self._source_origin(
                    statement.value,
                    source_names,
                    result.sources,
                )

                origin = (
                    source_origin
                    if source_origin is not None
                    else value_taint
                )

                for target in statement.targets:
                    self._assign_taint(
                        target,
                        origin,
                        tainted,
                    )

                # A sink can also appear inside an assignment RHS.
                self._check_sinks_in_expression(
                    statement.value,
                    tainted,
                    source_names,
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

                    origin = self._source_origin(
                        statement.value,
                        source_names,
                        result.sources,
                    )

                    if origin is None:
                        origin = self._expression_taint(
                            statement.value,
                            tainted,
                            source_names,
                        )

                    self._check_sinks_in_expression(
                        statement.value,
                        tainted,
                        source_names,
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

                existing_origin = None

                if isinstance(
                    statement.target,
                    ast.Name,
                ):
                    existing_origin = tainted.get(
                        statement.target.id
                    )

                value_origin = self._expression_taint(
                    statement.value,
                    tainted,
                    source_names,
                )

                origin = (
                    existing_origin
                    if existing_origin is not None
                    else value_origin
                )

                self._assign_taint(
                    statement.target,
                    origin,
                    tainted,
                )

                self._check_sinks_in_expression(
                    statement.value,
                    tainted,
                    source_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                continue

            # ----------------------------------------------------
            # IF
            # ----------------------------------------------------

            if isinstance(statement, ast.If):

                # Analyze the condition for possible sinks.
                self._check_sinks_in_expression(
                    statement.test,
                    tainted,
                    source_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                # Copy state for each branch.
                true_state = dict(tainted)
                false_state = dict(tainted)

                self._analyze_statements(
                    statement.body,
                    true_state,
                    source_names,
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
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                # Conservative merge:
                #
                # If a variable can be tainted on either path,
                # keep it tainted.
                merged = dict(tainted)

                for name, origin in true_state.items():
                    merged.setdefault(name, origin)

                for name, origin in false_state.items():
                    merged.setdefault(name, origin)

                tainted.clear()
                tainted.update(merged)

                continue

            # ----------------------------------------------------
            # LOOP
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
                    self._check_sinks_in_expression(
                        statement.test,
                        tainted,
                        source_names,
                        sink_names,
                        result,
                        data_flow,
                        def_use,
                        definition_ids,
                    )

                else:
                    self._check_sinks_in_expression(
                        statement.iter,
                        tainted,
                        source_names,
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
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                # Loop body may execute zero or more times, so
                # preserve taint from either state.
                for name, origin in loop_state.items():
                    tainted.setdefault(
                        name,
                        origin,
                    )

                self._analyze_statements(
                    statement.orelse,
                    tainted,
                    source_names,
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
                        sink_names,
                        result,
                        data_flow,
                        def_use,
                        definition_ids,
                    )

                continue

            # ----------------------------------------------------
            # EXPRESSION / FUNCTION CALL
            # ----------------------------------------------------

            if isinstance(statement, ast.Expr):

                self._check_sinks_in_expression(
                    statement.value,
                    tainted,
                    source_names,
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

                try_state = dict(tainted)

                self._analyze_statements(
                    statement.body,
                    try_state,
                    source_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                for handler in statement.handlers:

                    handler_state = dict(tainted)

                    self._analyze_statements(
                        handler.body,
                        handler_state,
                        source_names,
                        sink_names,
                        result,
                        data_flow,
                        def_use,
                        definition_ids,
                    )

                    for name, origin in handler_state.items():
                        try_state.setdefault(
                            name,
                            origin,
                        )

                self._analyze_statements(
                    statement.orelse,
                    try_state,
                    source_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                self._analyze_statements(
                    statement.finalbody,
                    try_state,
                    source_names,
                    sink_names,
                    result,
                    data_flow,
                    def_use,
                    definition_ids,
                )

                tainted.clear()
                tainted.update(try_state)

                continue

            # ----------------------------------------------------
            # Generic statement handling.
            # ----------------------------------------------------

            self._check_sinks_in_expression(
                statement,
                tainted,
                source_names,
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
    ) -> Optional[_TaintOrigin]:
        """
        Determine whether an expression contains tainted data.

        Examples:

            query = user_input

            query = "SELECT " + user_input

            query = f"SELECT {user_input}"

        All are considered tainted when user_input is tainted.
        """

        # Direct variable.
        if isinstance(node, ast.Name):
            return tainted.get(node.id)

        # Direct source call.
        source_origin = self._source_origin_from_call(
            node,
            source_names,
        )

        if source_origin is not None:
            return source_origin

        # Recursively inspect child expressions.
        for child in ast.iter_child_nodes(node):

            origin = self._expression_taint(
                child,
                tainted,
                source_names,
            )

            if origin is not None:
                return origin

        return None

    # ============================================================
    # SOURCE ORIGIN
    # ============================================================

    @staticmethod
    def _source_origin(
        node: ast.AST,
        source_names: set[str],
        sources: list[TaintSource],
    ) -> Optional[_TaintOrigin]:
        """
        Return the source origin contained in an expression.
        """

        for ast_node in ast.walk(node):

            if not isinstance(
                ast_node,
                ast.Call,
            ):
                continue

            name = TaintAnalyzer._call_name(
                ast_node
            )

            if name not in source_names:
                continue

            line = getattr(
                ast_node,
                "lineno",
                0,
            )

            return _TaintOrigin(
                source_name=name,
                source_line=line,
            )

        return None

    @staticmethod
    def _source_origin_from_call(
        node: ast.AST,
        source_names: set[str],
    ) -> Optional[_TaintOrigin]:
        """Return origin when node itself is a source call."""

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
        """
        Assign taint to a variable target.

        If the RHS is not tainted, the previous taint is removed
        because the assignment overwrites the previous value.
        """

        if isinstance(target, ast.Name):

            if origin is None:
                tainted.pop(
                    target.id,
                    None,
                )
            else:
                tainted[target.id] = origin

            return

        # Tuple/list unpacking.
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
        sink_names: set[str],
        result: TaintAnalysisResult,
        data_flow: DataFlowResult,
        def_use: DefUseResult,
        definition_ids: dict[tuple[str, int], str],
    ) -> None:
        """
        Find configured sink calls and determine whether any
        argument contains tainted data.
        """

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

            # ----------------------------------------------------
            # Check each sink argument.
            # ----------------------------------------------------

            for argument in ast_node.args:

                origin = self._expression_taint(
                    argument,
                    tainted,
                    source_names,
                )

                # Direct source inside sink.
                if origin is None:
                    origin = self._source_origin(
                        argument,
                        source_names,
                        result.sources,
                    )

                if origin is None:
                    continue

                variable = self._tainted_variable(
                    argument,
                    tainted,
                )

                # If the argument is an expression rather than a
                # simple variable, use a readable representation.
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

                path = (
                    origin.source_name,
                    variable,
                    sink_name,
                )

                result.findings.append(
                    TaintFlowFinding(
                        source_name=origin.source_name,
                        source_line=origin.source_line,
                        sink_name=sink_name,
                        sink_line=sink_line,
                        variable=variable,
                        definition_id=definition_id,
                        use_id=use_id,
                        path=path,
                    )
                )

    # ============================================================
    # VARIABLE EXTRACTION
    # ============================================================

    @staticmethod
    def _tainted_variable(
        node: ast.AST,
        tainted: dict[str, _TaintOrigin],
    ) -> Optional[str]:
        """
        Return the first tainted variable contained in an expression.
        """

        if isinstance(node, ast.Name):
            if node.id in tainted:
                return node.id

        for child in ast.iter_child_nodes(node):

            variable = TaintAnalyzer._tainted_variable(
                child,
                tainted,
            )

            if variable is not None:
                return variable

        return None

    @staticmethod
    def _expression_label(
        node: ast.AST,
    ) -> str:
        """
        Return a readable label for a non-variable tainted
        expression.
        """

        if isinstance(node, ast.Call):
            name = TaintAnalyzer._call_name(node)

            if name:
                return f"{name}(...)"

        if isinstance(node, ast.Constant):
            return repr(node.value)

        return "<tainted-expression>"

    # ============================================================
    # DEFINITION / USE MAPPING
    # ============================================================

    @staticmethod
    def _build_definition_id_map(
        data_flow: DataFlowResult,
    ) -> dict[tuple[str, int], str]:
        """
        Map:

            (variable, line) -> definition ID

        to the same D0, D1, ... ordering used by
        Reaching Definitions.
        """

        result: dict[
            tuple[str, int],
            str,
        ] = {}

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
        definition_ids: dict[tuple[str, int], str],
    ) -> str:
        """
        Find the latest definition of a variable before the sink.
        """

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

            if definition_id is None:
                continue

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
        """
        Find the Def-Use ID for a variable reaching a sink.
        """

        for chain in def_use.chains:

            if chain.variable != variable:
                continue

            if chain.use_line != sink_line:
                continue

            return chain.use_id

        return ""

    # ============================================================
    # SOURCE / SINK DISCOVERY
    # ============================================================

    @staticmethod
    def _find_sources(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_names: set[str],
    ) -> list[TaintSource]:
        """Find configured source calls."""

        sources: list[TaintSource] = []

        for node in TaintAnalyzer._walk_function(
            function_node
        ):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = TaintAnalyzer._call_name(node)

            if name not in source_names:
                continue

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
    def _find_sinks(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        sink_names: set[str],
    ) -> list[TaintSink]:
        """Find configured sink calls."""

        sinks: list[TaintSink] = []

        for node in TaintAnalyzer._walk_function(
            function_node
        ):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            name = TaintAnalyzer._call_name(node)

            if name not in sink_names:
                continue

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
    # AST HELPERS
    # ============================================================

    @staticmethod
    def _call_name(
        node: ast.Call,
    ) -> str:
        """Return the function/method name of a call."""

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
        """
        Walk the function while excluding nested functions/classes.
        """

        stack = list(function_node.body)

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
        """Extract function name from Code Guardian function ID."""

        if "::" in function_id:
            return function_id.rsplit(
                "::",
                1,
            )[-1]

        return function_id