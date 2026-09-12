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

    # Each use receives a stable local ID:
    #
    # U0, U1, U2, ...
    #
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
        """
        Build definition-use chains.

        For every variable use:

            1. Find the CFG node containing the use.
            2. Look at definitions reaching that CFG node.
            3. Keep only definitions of the same variable.
            4. Create one DefUseChain for each matching definition.
        """

        result = DefUseResult(
        function_name=reaching_definitions.function_name
    )

        # Reaching Definitions stores DefinitionRef objects.
        definitions_by_id = {
            definition.id: definition
            for definition in reaching_definitions.definitions
        }

     
        # Process every variable use
     

       
        # Process every variable use
        

        next_use_id = 0

        for use in data_flow.uses:

            # A variable use can be associated with one or more CFG
            # nodes. Usually there is one node.
            #
            # We consider all associated nodes and merge their reaching
            # definitions.
            reaching_definition_ids: set[str] = set()

            for cfg_node_id in use.cfg_node_ids:

                reaching_definition_ids.update(
                    reaching_definitions.in_sets.get(
                        cfg_node_id,
                        set(),
                    )
                )

           
            # Find definitions of the same variable.
           

            matching_definitions = []

            for definition_id in sorted(
                reaching_definition_ids
            ):

                definition_ref = definitions_by_id.get(
                    definition_id
                )

                if definition_ref is None:
                    continue

                definition = definition_ref.definition

                if definition.name != use.name:
                    continue

                matching_definitions.append(
                    definition_ref
                )

           
            # If no definition reaches this use, this use does not
            # participate in a Def-Use Chain.
            #
            # Example:
            #
            #     print(x)
            #
            # "print" is a Name/Load in the AST, but there is no
            # definition of print inside the function.
            #
            # Therefore it should not consume a Def-Use ID.
           

            if not matching_definitions:
                continue

            use_id = f"U{next_use_id}"
            result.use_ids[use_id] = next_use_id
            next_use_id += 1

           
            # Create one chain for every reaching definition.
           

            for definition_ref in matching_definitions:

                definition = definition_ref.definition

                result.chains.append(
                    DefUseChain(
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
                )

        return result