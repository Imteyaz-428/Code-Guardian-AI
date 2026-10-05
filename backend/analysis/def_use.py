"""
Definition-Use Chain Analysis.

Milestone 3 of Code Guardian AI Data Flow Analysis.

This module connects:

    Variable Definition
            ↓
    Reaching Definition
            ↓
       Variable Use

It builds on the existing:
    - DataFlowAnalyzer
    - ReachingDefinitionsAnalyzer
    - ControlFlowGraph

This module does not modify any existing analysis layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.analysis.data_flow import DataFlowResult
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsResult,
)


@dataclass(frozen=True)
class DefUseChain:
    """
    Represents a relationship between one definition and one use.

    Example:

        x = 10          # D0
        print(x)        # U0

        D0 → U0
    """

    definition_id: str
    use_id: str

    variable: str

    definition_line: int
    use_line: int

    definition_kind: str
    use_context: str

    definition_cfg_node_ids: tuple[int, ...] = field(
        default_factory=tuple
    )

    use_cfg_node_ids: tuple[int, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict:
        """Convert the chain into a JSON-friendly dictionary."""

        return {
            "definition_id": self.definition_id,
            "use_id": self.use_id,
            "variable": self.variable,
            "definition_line": self.definition_line,
            "use_line": self.use_line,
            "definition_kind": self.definition_kind,
            "use_context": self.use_context,
            "definition_cfg_node_ids": list(
                self.definition_cfg_node_ids
            ),
            "use_cfg_node_ids": list(
                self.use_cfg_node_ids
            ),
        }


@dataclass
class DefUseResult:
    """
    Complete definition-use analysis for one function.
    """

    function_name: str

    chains: list[DefUseChain] = field(
        default_factory=list
    )

    # Stable local IDs for valid variable uses.
    #
    # U0, U1, U2, ...
    #
    # use_ids maps:
    #     "U0" -> 0
    #     "U1" -> 1
    #     "U2" -> 2
    use_ids: dict[str, int] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict:
        """Convert the complete result to a dictionary."""

        return {
            "function": self.function_name,
            "chains": [
                chain.to_dict()
                for chain in self.chains
            ],
        }

    @property
    def chain_count(self) -> int:
        """Return the number of definition-use chains."""

        return len(self.chains)

    def get_chains_for_use(
        self,
        use_id: str,
    ) -> list[DefUseChain]:
        """Return all definitions reaching one use."""

        return [
            chain
            for chain in self.chains
            if chain.use_id == use_id
        ]

    def get_chains_for_definition(
        self,
        definition_id: str,
    ) -> list[DefUseChain]:
        """Return all uses reached by one definition."""

        return [
            chain
            for chain in self.chains
            if chain.definition_id == definition_id
        ]


class DefUseAnalyzer:
    """
    Builds definition-use chains.

    Input:

        DataFlowResult
              +
        ReachingDefinitionsResult

    Output:

        DefUseResult
    """

    def analyze(
        self,
        data_flow: DataFlowResult,
        reaching_definitions: ReachingDefinitionsResult,
    ) -> DefUseResult:

        # DataFlowResult uses `function_id`.
        function_name = data_flow.function_id.split("::")[-1]

        result = DefUseResult(
            function_name=function_name
        )

        next_use_id = 0

        for use in data_flow.uses:

            # ---------------------------------------------------------
            # Ignore function/call names.
            #
            # Example:
            #
            #     print(x)
            #
            # `print` is a call, not a variable use.
            # ---------------------------------------------------------
            if use.context == "call":
                continue

            # ---------------------------------------------------------
            # Find all definitions reaching the CFG node(s) where
            # this variable is used.
            # ---------------------------------------------------------

            reaching_definition_refs = []

            seen_definition_ids: set[str] = set()

            for node_id in use.cfg_node_ids:

                node_definitions = (
                    reaching_definitions.get_reaching_definitions(
                        node_id
                    )
                )

                for definition_ref in node_definitions:

                    # Avoid duplicate definitions if the same
                    # definition reaches multiple CFG nodes.
                    if definition_ref.id in seen_definition_ids:
                        continue

                    # Only connect the same variable.
                    if definition_ref.definition.name != use.name:
                        continue

                    seen_definition_ids.add(
                        definition_ref.id
                    )

                    reaching_definition_refs.append(
                        definition_ref
                    )

            # ---------------------------------------------------------
            # No matching definition means this variable use does not
            # produce a Def-Use chain.
            #
            # Therefore it does NOT consume a U ID.
            # ---------------------------------------------------------

            if not reaching_definition_refs:
                continue

            # ---------------------------------------------------------
            # Assign stable use ID.
            # ---------------------------------------------------------

            use_id = f"U{next_use_id}"

            result.use_ids[use_id] = next_use_id

            next_use_id += 1

            # ---------------------------------------------------------
            # Create one DefUseChain for every reaching definition.
            #
            # Example:
            #
            #     if condition:
            #         x = 10       # D1
            #     else:
            #         x = 20       # D2
            #
            #     print(x)         # U0
            #
            # Result:
            #
            #     D1 → U0
            #     D2 → U0
            # ---------------------------------------------------------

            for definition_ref in reaching_definition_refs:

                definition = definition_ref.definition

                chain = DefUseChain(
                    definition_id=definition_ref.id,
                    use_id=use_id,
                    variable=use.name,
                    definition_line=definition.line,
                    use_line=use.line,
                    definition_kind=definition.kind,
                    use_context=use.context,
                    definition_cfg_node_ids=tuple(
                        definition.cfg_node_ids
                    ),
                    use_cfg_node_ids=tuple(
                        use.cfg_node_ids
                    ),
                )

                result.chains.append(chain)

        return result