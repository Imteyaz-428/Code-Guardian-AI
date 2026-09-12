"""
Taint Analysis.

Milestone 1 of Code Guardian AI Taint Analysis.

This module detects simple intra-procedural flows of potentially
untrusted data:

    SOURCE
       ↓
    variable definition
       ↓
    variable definition
       ↓
    SINK

The analysis is intentionally isolated.

It does NOT yet:
    - modify ProjectAnalyzer
    - modify API schemas
    - modify frontend
    - perform interprocedural analysis
    - generate patches
    - execute code
    - perform machine-learning risk prediction

It builds on the existing:

    DataFlowResult
    DefUseResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import ast

from backend.analysis.data_flow import DataFlowResult
from backend.analysis.def_use import DefUseResult


@dataclass(frozen=True)
class TaintSource:
    """
    Represents a source of potentially untrusted data.

    Example:

        user_input = request_input()

    The source is:

        request_input
    """

    name: str
    line: int
    kind: str = "source"

    def to_dict(self) -> dict[str, Any]:
        """Convert the source into a JSON-friendly dictionary."""

        return {
            "name": self.name,
            "line": self.line,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class TaintSink:
    """
    Represents a sensitive operation receiving potentially tainted data.

    Example:

        execute(query)

    The sink is:

        execute
    """

    name: str
    line: int
    kind: str = "sink"

    def to_dict(self) -> dict[str, Any]:
        """Convert the sink into a JSON-friendly dictionary."""

        return {
            "name": self.name,
            "line": self.line,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class TaintFlowFinding:
    """
    Represents one tainted flow from a source to a sink.
    """

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
        """Convert the finding into a JSON-friendly dictionary."""

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


@dataclass
class TaintAnalysisResult:
    """
    Complete taint-analysis result for one function.
    """

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
        """Return the number of tainted flows."""

        return len(self.findings)

    @property
    def has_findings(self) -> bool:
        """Return True when tainted flows were detected."""

        return bool(self.findings)

    def to_dict(self) -> dict[str, Any]:
        """Convert the complete result into a dictionary."""

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


class TaintAnalyzer:
    """
    Performs first-level intra-procedural taint analysis.

    The analyzer identifies:

        source call
            ↓
        variable definition
            ↓
        Def-Use chain(s)
            ↓
        sink call

    Source and sink names are configurable.

    Example:

        source_names = {"request_input"}
        sink_names = {"execute"}

    Then:

        user_input = request_input()
        execute(user_input)

    produces a taint finding.
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
        Analyze one function for source-to-sink taint flows.

        Parameters
        ----------
        function_node:
            AST node for the function being analyzed.

        data_flow:
            Existing DataFlowResult for the same function.

        def_use:
            Existing DefUseResult for the same function.

        source_names:
            Names considered taint sources.

        sink_names:
            Names considered taint sinks.

        Returns
        -------
        TaintAnalysisResult
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

        result = TaintAnalysisResult(
            function_name=data_flow.function_id.split("::")[-1]
        )

        # ---------------------------------------------------------
        # DISCOVER SOURCES
        # ---------------------------------------------------------

        result.sources.extend(
            self._find_sources(
                function_node=function_node,
                source_names=source_names_set,
            )
        )

        # ---------------------------------------------------------
        # DISCOVER SINKS
        # ---------------------------------------------------------

        result.sinks.extend(
            self._find_sinks(
                function_node=function_node,
                sink_names=sink_names_set,
            )
        )

        # No sources or sinks means there can be no tainted flow.
        if not result.sources or not result.sinks:
            return result

        # ---------------------------------------------------------
        # MAP DEFINITIONS TO DEF-USE CHAINS
        # ---------------------------------------------------------

        chains_by_definition: dict[
            str,
            list,
        ] = {}

        for chain in def_use.chains:
            chains_by_definition.setdefault(
                chain.definition_id,
                [],
            ).append(chain)

        # ---------------------------------------------------------
        # FIND SOURCE-TAINTED DEFINITIONS
        # ---------------------------------------------------------

        tainted_definitions: dict[
            str,
            tuple[TaintSource, str],
        ] = {}

        for source in result.sources:

            source_definition_ids = (
                self._definitions_created_by_source(
                    source=source,
                    data_flow=data_flow,
                )
            )

            for definition_id, variable in (
                source_definition_ids
            ):
                tainted_definitions[definition_id] = (
                    source,
                    variable,
                )

        # ---------------------------------------------------------
        # PROPAGATE TAINT THROUGH DEF-USE CHAINS
        # ---------------------------------------------------------

        changed = True

        while changed:
            changed = False

            for definition_id, (
                source,
                variable,
            ) in list(
                tainted_definitions.items()
            ):

                for chain in chains_by_definition.get(
                    definition_id,
                    [],
                ):

                    # The chain represents:
                    #
                    # definition → use
                    #
                    # If the use variable is assigned to another
                    # definition, that definition can become tainted.
                    #
                    # The current milestone handles direct variable
                    # propagation.

                    next_definition_ids = (
                        self._definitions_for_variable_at_line(
                            variable=chain.variable,
                            line=chain.use_line,
                            data_flow=data_flow,
                        )
                    )

                    for next_definition_id in (
                        next_definition_ids
                    ):
                        if (
                            next_definition_id
                            not in tainted_definitions
                        ):
                            tainted_definitions[
                                next_definition_id
                            ] = (
                                source,
                                chain.variable,
                            )

                            changed = True

        # ---------------------------------------------------------
        # MATCH TAINTED DATA TO SINKS
        # ---------------------------------------------------------

        for definition_id, (
            source,
            variable,
        ) in tainted_definitions.items():

            for chain in chains_by_definition.get(
                definition_id,
                [],
            ):

                for sink in result.sinks:

                    if chain.use_line != sink.line:
                        continue

                    result.findings.append(
                        TaintFlowFinding(
                            source_name=source.name,
                            source_line=source.line,
                            sink_name=sink.name,
                            sink_line=sink.line,
                            variable=variable,
                            definition_id=definition_id,
                            use_id=chain.use_id,
                            path=(
                                source.name,
                                variable,
                                sink.name,
                            ),
                        )
                    )

        return result

    # -------------------------------------------------------------
    # SOURCE DISCOVERY
    # -------------------------------------------------------------

    @staticmethod
    def _find_sources(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_names: set[str],
    ) -> list[TaintSource]:
        """
        Find configured source calls inside the function.

        Example:

            value = request_input()

        produces:

            TaintSource(
                name="request_input",
                line=2,
            )
        """

        sources: list[TaintSource] = []

        for node in ast.walk(function_node):

            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            else:
                continue

            if name not in source_names:
                continue

            sources.append(
                TaintSource(
                    name=name,
                    line=getattr(node, "lineno", 0),
                )
            )

        return sources

    # -------------------------------------------------------------
    # SINK DISCOVERY
    # -------------------------------------------------------------

    @staticmethod
    def _find_sinks(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        sink_names: set[str],
    ) -> list[TaintSink]:
        """
        Find configured sink calls inside the function.

        Example:

            execute(value)

        produces:

            TaintSink(
                name="execute",
                line=3,
            )
        """

        sinks: list[TaintSink] = []

        for node in ast.walk(function_node):

            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            else:
                continue

            if name not in sink_names:
                continue

            sinks.append(
                TaintSink(
                    name=name,
                    line=getattr(node, "lineno", 0),
                )
            )

        return sinks

    # -------------------------------------------------------------
    # SOURCE → DEFINITION
    # -------------------------------------------------------------

    @staticmethod
    def _definitions_created_by_source(
        source: TaintSource,
        data_flow: DataFlowResult,
    ) -> list[tuple[str, str]]:
        """
        Find definitions on the same line as a source call.

        Example:

            user_input = request_input()

        Data Flow:

            definition:
                user_input

        source:

            request_input

        returns the definition candidate.
        """

        definitions: list[tuple[str, str]] = []

        for index, definition in enumerate(
            data_flow.definitions
        ):
            if definition.line != source.line:
                continue

            definition_id = f"D{index}"

            # Parameters are never created by a source call.
            if definition.kind == "parameter":
                continue

            definitions.append(
                (
                    definition_id,
                    definition.name,
                )
            )

        return definitions

    # -------------------------------------------------------------
    # FIND DEFINITIONS FOR PROPAGATION
    # -------------------------------------------------------------

    @staticmethod
    def _definitions_for_variable_at_line(
        variable: str,
        line: int,
        data_flow: DataFlowResult,
    ) -> list[str]:
        """
        Find definitions of a variable at or after a use.

        This helper intentionally keeps propagation conservative
        for the first milestone.
        """

        definitions: list[str] = []

        for index, definition in enumerate(
            data_flow.definitions
        ):
            if definition.name != variable:
                continue

            if definition.line < line:
                continue

            definitions.append(
                f"D{index}"
            )

        return definitions