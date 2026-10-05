"""
Risk Label Generation
=====================

Generate deterministic weak-risk labels from static-analysis
evidence already represented in the Unified Code Graph.

These are weak training labels, not ground-truth security labels.

Risk levels:

    0 -> LOW
    1 -> MEDIUM
    2 -> HIGH
    3 -> CRITICAL
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
    UnifiedCodeGraph,
)


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class RiskEvidence:
    reason: str
    points: float


@dataclass
class RiskLabel:
    node_id: str
    score: float
    level: RiskLevel
    evidence: list[RiskEvidence] = field(
        default_factory=list
    )

    @property
    def label(self) -> int:
        return int(self.level)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "score": self.score,
            "level": self.level.name,
            "label": self.label,
            "evidence": [
                {
                    "reason": evidence.reason,
                    "points": evidence.points,
                }
                for evidence in self.evidence
            ],
        }


class RiskLabelGenerator:
    """
    Generate deterministic weak-risk labels from the
    UnifiedCodeGraph.
    """

    def __init__(
        self,
        graph: UnifiedCodeGraph,
    ) -> None:

        self.graph = graph

    def generate(
        self,
    ) -> dict[str, RiskLabel]:

        labels: dict[str, RiskLabel] = {}

        for node_id in sorted(
            self.graph.nodes.keys()
        ):
            labels[node_id] = (
                self._generate_for_node(
                    node_id
                )
            )

        return labels

    def _generate_for_node(
        self,
        node_id: str,
    ) -> RiskLabel:

        score = 0.0

        evidence: list[RiskEvidence] = []

        incoming = self.graph.get_edges_to(
            node_id
        )

        outgoing = self.graph.get_edges_from(
            node_id
        )

        # ----------------------------------------------------
        # Taint Flow
        # ----------------------------------------------------

        taint_flow = self._count_incident(
            incoming,
            outgoing,
            CodeGraphEdgeType.TAINT_FLOW,
        )

        if taint_flow > 0:

            points = 4.0 * taint_flow

            score += points

            evidence.append(
                RiskEvidence(
                    reason=(
                        "Taint-flow relationship "
                        "detected"
                    ),
                    points=points,
                )
            )

        # ----------------------------------------------------
        # Data Dependency
        # ----------------------------------------------------

        data_dependency = self._count_incident(
            incoming,
            outgoing,
            CodeGraphEdgeType.DATA_DEPENDENCY,
        )

        if data_dependency > 0:

            points = 1.5 * data_dependency

            score += points

            evidence.append(
                RiskEvidence(
                    reason=(
                        "Data dependency "
                        "relationship detected"
                    ),
                    points=points,
                )
            )

        # ----------------------------------------------------
        # Def-Use
        # ----------------------------------------------------

        def_use = self._count_incident(
            incoming,
            outgoing,
            CodeGraphEdgeType.DEF_USE,
        )

        if def_use > 0:

            points = 0.5 * def_use

            score += points

            evidence.append(
                RiskEvidence(
                    reason=(
                        "Definition-use "
                        "relationship detected"
                    ),
                    points=points,
                )
            )

        # ----------------------------------------------------
        # High Call Fan-Out
        # ----------------------------------------------------

        calls = self._count_outgoing(
            outgoing,
            CodeGraphEdgeType.CALLS,
        )

        if calls >= 5:

            points = 2.0

            score += points

            evidence.append(
                RiskEvidence(
                    reason=(
                        "High outgoing call "
                        "connectivity"
                    ),
                    points=points,
                )
            )

        # ----------------------------------------------------
        # High Dependency Fan-Out
        # ----------------------------------------------------

        dependencies = self._count_outgoing(
            outgoing,
            CodeGraphEdgeType.DEPENDS_ON,
        )

        if dependencies >= 5:

            points = 1.0

            score += points

            evidence.append(
                RiskEvidence(
                    reason=(
                        "High dependency "
                        "connectivity"
                    ),
                    points=points,
                )
            )

        # ----------------------------------------------------
        # General Connectivity
        # ----------------------------------------------------

        connectivity = (
            len(incoming)
            + len(outgoing)
        )

        if connectivity >= 10:

            points = 1.0

            score += points

            evidence.append(
                RiskEvidence(
                    reason=(
                        "Highly connected "
                        "graph node"
                    ),
                    points=points,
                )
            )

        level = self._score_to_level(
            score
        )

        return RiskLabel(
            node_id=node_id,
            score=score,
            level=level,
            evidence=evidence,
        )

    @staticmethod
    def _score_to_level(
        score: float,
    ) -> RiskLevel:

        if score >= 7.0:
            return RiskLevel.CRITICAL

        if score >= 4.0:
            return RiskLevel.HIGH

        if score >= 2.0:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    @staticmethod
    def _count_outgoing(
        edges,
        edge_type: CodeGraphEdgeType,
    ) -> int:

        return sum(
            edge.edge_type == edge_type
            for edge in edges
        )

    @staticmethod
    def _count_incident(
        incoming,
        outgoing,
        edge_type: CodeGraphEdgeType,
    ) -> int:

        return (
            sum(
                edge.edge_type == edge_type
                for edge in incoming
            )
            +
            sum(
                edge.edge_type == edge_type
                for edge in outgoing
            )
        )