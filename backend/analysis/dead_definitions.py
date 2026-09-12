"""
Dead Definition Analysis.

A definition is considered dead when the value assigned by that
definition is never used by any valid Def-Use chain.

Pipeline:

    Data Flow
        ↓
    Reaching Definitions
        ↓
    Def-Use Chains
        ↓
    Dead Definition Analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.analysis.def_use import DefUseResult
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsResult,
)


@dataclass(frozen=True)
class DeadDefinitionFinding:
    """
    Represents a definition whose value is never used.
    """

    definition_id: str
    variable: str
    line: int
    definition_kind: str
    cfg_node_ids: tuple[int, ...] = field(
        default_factory=tuple
    )
    reason: str = (
        "Definition is never used by any valid data-flow use."
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert the finding into a JSON-friendly dictionary."""

        return {
            "definition_id": self.definition_id,
            "variable": self.variable,
            "line": self.line,
            "definition_kind": self.definition_kind,
            "cfg_node_ids": list(self.cfg_node_ids),
            "reason": self.reason,
        }


@dataclass
class DeadDefinitionResult:
    """
    Complete dead-definition analysis result for one function.
    """

    function_name: str

    findings: list[DeadDefinitionFinding] = field(
        default_factory=list
    )

    @property
    def finding_count(self) -> int:
        """Return the number of dead definitions."""

        return len(self.findings)

    @property
    def has_findings(self) -> bool:
        """Return True when dead definitions exist."""

        return bool(self.findings)

    def to_dict(self) -> dict[str, Any]:
        """Convert the result into a JSON-friendly dictionary."""

        return {
            "function": self.function_name,
            "finding_count": self.finding_count,
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
        }


class DeadDefinitionAnalyzer:
    """
    Detect definitions whose values are never used.

    A definition is considered live when its definition ID appears
    in at least one Def-Use chain.

    A definition with no outgoing Def-Use chain is considered dead.

    Function parameters are excluded by default because an unused
    parameter is a different kind of code-quality finding and should
    not be treated as a dead assignment.
    """

    def analyze(
        self,
        reaching_definitions: ReachingDefinitionsResult,
        def_use: DefUseResult,
        include_parameters: bool = False,
    ) -> DeadDefinitionResult:
        """
        Find definitions that have no valid use.

        Parameters
        ----------
        reaching_definitions:
            Result containing every definition and its definition ID.

        def_use:
            Def-Use chains connecting definitions to their uses.

        include_parameters:
            Whether function parameters should also be checked.

            False:
                Parameters are ignored.

            True:
                Unused parameters are reported as dead definitions.
        """

        result = DeadDefinitionResult(
            function_name=reaching_definitions.function_name
        )

        # ---------------------------------------------------------
        # COLLECT DEFINITIONS THAT ARE ACTUALLY USED
        # ---------------------------------------------------------
        #
        # Every DefUseChain contains:
        #
        #     definition_id
        #
        # Therefore, a definition is live when its ID appears in
        # at least one chain.
        # ---------------------------------------------------------

        used_definition_ids: set[str] = {
            chain.definition_id
            for chain in def_use.chains
        }

        # ---------------------------------------------------------
        # CHECK EVERY DEFINITION
        # ---------------------------------------------------------

        for definition_ref in reaching_definitions.definitions:

            definition = definition_ref.definition

            # Parameters are intentionally excluded by default.
            #
            # Example:
            #
            #     def process(user_id):
            #         return 10
            #
            # user_id being unused is not necessarily a dead
            # assignment. It is better handled as an unused
            # parameter finding.
            if (
                not include_parameters
                and definition.kind == "parameter"
            ):
                continue

            # If this definition participates in at least one
            # valid Def-Use chain, its value is used.
            if definition_ref.id in used_definition_ids:
                continue

            # Otherwise, the definition is dead.
            result.findings.append(
                DeadDefinitionFinding(
                    definition_id=definition_ref.id,
                    variable=definition.name,
                    line=definition.line,
                    definition_kind=definition.kind,
                    cfg_node_ids=tuple(
                        definition.cfg_node_ids
                    ),
                )
            )

        return result