"""
Use-Before-Definition Analysis.

Milestone 4 of Code Guardian AI Data Flow Analysis.

This module detects variables that are not definitely defined
on every control-flow path before their use.

Pipeline:

    AST
     ↓
    CFG
     ↓
    Data Flow
     ↓
    Reaching Definitions
     ↓
    Definite Definitions
     ↓
    Use-Before-Definition
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.analysis.data_flow import DataFlowResult
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsResult,
)


@dataclass(frozen=True)
class UseBeforeDefinitionFinding:
    """
    Represents one variable use that is not definitely defined
    at the point of use.
    """

    variable: str

    line: int

    context: str

    use_id: str

    cfg_node_ids: tuple[int, ...] = field(
        default_factory=tuple
    )

    reason: str = (
        "Variable is used before a definition reaches this point."
    )

    def to_dict(self) -> dict:
        """Convert the finding into a JSON-friendly dictionary."""

        return {
            "variable": self.variable,
            "line": self.line,
            "context": self.context,
            "use_id": self.use_id,
            "cfg_node_ids": list(self.cfg_node_ids),
            "reason": self.reason,
        }


@dataclass
class UseBeforeDefinitionResult:
    """
    Complete use-before-definition analysis result for one function.
    """

    function_name: str

    findings: list[UseBeforeDefinitionFinding] = field(
        default_factory=list
    )

    def to_dict(self) -> dict:
        """Convert the result into a dictionary."""

        return {
            "function": self.function_name,
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
        }

    @property
    def finding_count(self) -> int:
        """Return the number of findings."""

        return len(self.findings)

    @property
    def has_findings(self) -> bool:
        """Return True when findings exist."""

        return bool(self.findings)


class UseBeforeDefinitionAnalyzer:
    """
    Detect variables that are not definitely defined before use.

    Important distinction:

        Reaching Definitions = MAY analysis

            "Can a definition reach this point?"

        Use-Before-Definition = MUST analysis

            "Is the variable defined on EVERY path
             reaching this point?"

    Therefore, this analyzer performs a small forward
    definite-definition analysis on the existing CFG.
    """

    def analyze(
        self,
        data_flow: DataFlowResult,
        reaching_definitions: ReachingDefinitionsResult,
    ) -> UseBeforeDefinitionResult:
        """
        Analyze variable uses.

        A variable is safe when it is definitely defined on every
        path reaching the CFG node containing the use.

        Function-call targets such as:

            print(x)
            calculate(x)

        are ignored because Data Flow marks them with:

            context="call"
        """

        result = UseBeforeDefinitionResult(
            function_name=reaching_definitions.function_name
        )

        # ---------------------------------------------------------
        # Build DEFINITIONS AT EACH CFG NODE
        # ---------------------------------------------------------

        definition_by_id = {
            definition.id: definition
            for definition in reaching_definitions.definitions
        }

        definitions_at_node: dict[int, set[str]] = {}

        for node_id, generated_ids in (
            reaching_definitions.gen.items()
        ):
            names: set[str] = set()

            for definition_id in generated_ids:
                definition_ref = definition_by_id.get(
                    definition_id
                )

                if definition_ref is not None:
                    names.add(
                        definition_ref.definition.name
                    )

            definitions_at_node[node_id] = names

        # ---------------------------------------------------------
        # MUST-DEFINED ANALYSIS
        # ---------------------------------------------------------
        #
        # For every CFG node:
        #
        #     IN[n] = intersection(OUT[p])
        #
        # for all predecessors p.
        #
        # This is the key difference from Reaching Definitions.
        #
        # Reaching Definitions uses:
        #
        #     UNION
        #
        # because it is a MAY analysis.
        #
        # Here we use:
        #
        #     INTERSECTION
        #
        # because we need a MUST analysis.
        # ---------------------------------------------------------

        must_in: dict[int, set[str]] = {}
        must_out: dict[int, set[str]] = {}

        node_ids = list(reaching_definitions.in_sets.keys())

        # Start with empty sets.
        for node_id in node_ids:
            must_in[node_id] = set()
            must_out[node_id] = set(
                definitions_at_node.get(
                    node_id,
                    set(),
                )
            )

        changed = True

        while changed:
            changed = False

            for node_id in node_ids:

                predecessors = (
                    reaching_definitions.predecessors.get(
                        node_id,
                        [],
                    )
                )

                # -------------------------------------------------
                # ENTRY NODE
                # -------------------------------------------------
                #
                # A node with no predecessors is an entry point.
                #
                # Function parameters are definitions associated
                # with the ENTRY node by DataFlowAnalyzer.
                #
                # Therefore:
                #
                #     IN[ENTRY] = {}
                #
                # and:
                #
                #     OUT[ENTRY] = parameter definitions
                # -------------------------------------------------

                if not predecessors:
                    new_in = set()

                else:
                    # Start with OUT of the first predecessor.
                    new_in = set(
                        must_out.get(
                            predecessors[0],
                            set(),
                        )
                    )

                    # Every other predecessor must also have
                    # the variable defined.
                    for predecessor in predecessors[1:]:
                        new_in.intersection_update(
                            must_out.get(
                                predecessor,
                                set(),
                            )
                        )

                # Definitions created by this node become definitely
                # defined after the node.
                new_out = (
                    new_in
                    |
                    definitions_at_node.get(
                        node_id,
                        set(),
                    )
                )

                if new_in != must_in[node_id]:
                    must_in[node_id] = new_in
                    changed = True

                if new_out != must_out[node_id]:
                    must_out[node_id] = new_out
                    changed = True

        # ---------------------------------------------------------
        # CHECK EVERY VARIABLE USE
        # ---------------------------------------------------------

        for use_index, use in enumerate(data_flow.uses):

            use_id = f"U{use_index}"

            # Function-call targets are not variables.
            #
            # Example:
            #
            #     print(x)
            #
            # Data Flow:
            #
            #     print -> call
            #     x     -> load
            #
            # UBD ignores "print".
            if use.context == "call":
                continue

            # If a use has no CFG association, we cannot prove
            # that a definition reaches it.
            if not use.cfg_node_ids:
                result.findings.append(
                    UseBeforeDefinitionFinding(
                        variable=use.name,
                        line=use.line,
                        context=use.context,
                        use_id=use_id,
                        cfg_node_ids=tuple(
                            use.cfg_node_ids
                        ),
                    )
                )

                continue

            # A variable must be definitely defined at EVERY
            # CFG node associated with this use.
            is_definitely_defined = True

            for cfg_node_id in use.cfg_node_ids:

                if use.name not in must_in.get(
                    cfg_node_id,
                    set(),
                ):
                    is_definitely_defined = False
                    break

            # If the variable is not definitely defined,
            # report a finding.
            if not is_definitely_defined:

                result.findings.append(
                    UseBeforeDefinitionFinding(
                        variable=use.name,
                        line=use.line,
                        context=use.context,
                        use_id=use_id,
                        cfg_node_ids=tuple(
                            use.cfg_node_ids
                        ),
                    )
                )

        return result