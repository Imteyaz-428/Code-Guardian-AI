"""
Graph Feature Extraction
========================

Extract deterministic numerical features from the Unified Code Graph.

Pipeline:

    UnifiedCodeGraph
          ↓
    GraphFeatureExtractor
          ↓
    node_id -> feature vector
          ↓
    GraphDatasetBuilder
          ↓
    ML / GNN
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.analysis.unified_code_graph import (
    CodeGraphEdge,
    CodeGraphEdgeType,
    CodeGraphNode,
    UnifiedCodeGraph,
)


@dataclass(frozen=True)
class GraphFeatureSchema:
    """
    Defines the exact and stable order of graph features.

    IMPORTANT:
    Once ML training starts, this order must not be changed
    without retraining the model.
    """

    names: tuple[str, ...] = (
        # Node type
        "is_file",
        "is_function",
        "is_method",
        "is_cfg_node",
        "is_definition",
        "is_use",

        # Source context
        "has_source_location",
        "has_function_context",

        # General connectivity
        "incoming_edge_count",
        "outgoing_edge_count",

        # Relationship counts
        "contains_count",
        "nests_count",
        "cfg_node_count",
        "control_flow_count",
        "calls_count",
        "depends_on_count",
        "defines_count",
        "uses_count",
        "def_use_count",
        "taint_flow_count",
        "data_dependency_count",
        "inherits_count",
        "overrides_count",
    )

    @property
    def size(self) -> int:
        return len(self.names)


class GraphFeatureExtractor:
    """
    Extract numerical node features from a UnifiedCodeGraph.
    """

    def __init__(
        self,
        graph: UnifiedCodeGraph,
    ) -> None:

        self.graph = graph

        self.schema = GraphFeatureSchema()

    # ========================================================
    # Public API
    # ========================================================

    def extract(
        self,
    ) -> dict[str, list[float]]:
        """
        Extract features for every graph node.

        Returns:

            {
                node_id: [
                    feature_1,
                    feature_2,
                    ...
                ]
            }
        """

        features: dict[
            str,
            list[float],
        ] = {}

        for node_id in sorted(
            self.graph.nodes.keys()
        ):

            node = self.graph.nodes[
                node_id
            ]

            features[node_id] = (
                self._extract_node_features(
                    node
                )
            )

        return features

    # ========================================================
    # Single Node
    # ========================================================

    def _extract_node_features(
        self,
        node: CodeGraphNode,
    ) -> list[float]:

        incoming_edges = (
            self.graph.get_edges_to(
                node.id
            )
        )

        outgoing_edges = (
            self.graph.get_edges_from(
                node.id
            )
        )

        incoming_count = len(
            incoming_edges
        )

        outgoing_count = len(
            outgoing_edges
        )

        # ----------------------------------------------------
        # Node type
        # ----------------------------------------------------

        is_file = self._binary(
            node.node_type == "file"
        )

        is_function = self._binary(
            node.node_type == "function"
        )

        is_method = self._binary(
            node.node_type == "method"
        )

        is_cfg_node = self._binary(
            node.node_type == "cfg_node"
        )

        is_definition = self._binary(
            node.node_type == "definition"
        )

        is_use = self._binary(
            node.node_type == "use"
        )

        # ----------------------------------------------------
        # Source context
        # ----------------------------------------------------

        has_source_location = self._binary(
            node.file is not None
            and node.line is not None
        )

        has_function_context = self._binary(
            node.function_id is not None
        )

        # ----------------------------------------------------
        # Relationship counts
        # ----------------------------------------------------

        contains_count = self._count_outgoing(
            outgoing_edges,
            CodeGraphEdgeType.CONTAINS,
        )

        nests_count = self._count_outgoing(
            outgoing_edges,
            CodeGraphEdgeType.NESTS,
        )

        cfg_node_count = self._count_outgoing(
            outgoing_edges,
            CodeGraphEdgeType.HAS_CFG_NODE,
        )

        control_flow_count = (
            self._count_incident(
                incoming_edges,
                outgoing_edges,
                CodeGraphEdgeType.CONTROL_FLOW,
            )
        )

        calls_count = self._count_outgoing(
            outgoing_edges,
            CodeGraphEdgeType.CALLS,
        )

        depends_on_count = (
            self._count_outgoing(
                outgoing_edges,
                CodeGraphEdgeType.DEPENDS_ON,
            )
        )

        defines_count = self._count_outgoing(
            outgoing_edges,
            CodeGraphEdgeType.DEFINES,
        )

        uses_count = self._count_outgoing(
            outgoing_edges,
            CodeGraphEdgeType.USES,
        )

        def_use_count = (
            self._count_incident(
                incoming_edges,
                outgoing_edges,
                CodeGraphEdgeType.DEF_USE,
            )
        )

        taint_flow_count = (
            self._count_incident(
                incoming_edges,
                outgoing_edges,
                CodeGraphEdgeType.TAINT_FLOW,
            )
        )

        data_dependency_count = (
            self._count_incident(
                incoming_edges,
                outgoing_edges,
                CodeGraphEdgeType.DATA_DEPENDENCY,
            )
        )

        inherits_count = (
            self._count_outgoing(
                outgoing_edges,
                CodeGraphEdgeType.INHERITS,
            )
        )

        overrides_count = (
            self._count_outgoing(
                outgoing_edges,
                CodeGraphEdgeType.OVERRIDES,
            )
        )

        # ----------------------------------------------------
        # Final vector
        # ----------------------------------------------------

        vector = [
            is_file,
            is_function,
            is_method,
            is_cfg_node,
            is_definition,
            is_use,

            has_source_location,
            has_function_context,

            float(incoming_count),
            float(outgoing_count),

            float(contains_count),
            float(nests_count),
            float(cfg_node_count),
            float(control_flow_count),
            float(calls_count),
            float(depends_on_count),
            float(defines_count),
            float(uses_count),
            float(def_use_count),
            float(taint_flow_count),
            float(data_dependency_count),
            float(inherits_count),
            float(overrides_count),
        ]

        if len(vector) != self.schema.size:

            raise RuntimeError(
                "Graph feature vector size does not "
                "match GraphFeatureSchema."
            )

        return vector

    # ========================================================
    # Feature Names
    # ========================================================

    def feature_names(self) -> tuple[str, ...]:
        """
        Return feature names in the exact order used
        by the generated vectors.
        """

        return self.schema.names

    # ========================================================
    # Feature Matrix
    # ========================================================

    def feature_matrix(
        self,
    ) -> tuple[
        list[str],
        list[list[float]],
    ]:
        """
        Return:

            node_ids
            feature_matrix

        using deterministic node ordering.
        """

        features = self.extract()

        node_ids = sorted(
            features.keys()
        )

        matrix = [
            features[node_id]
            for node_id in node_ids
        ]

        return (
            node_ids,
            matrix,
        )

    # ========================================================
    # Helpers
    # ========================================================

    @staticmethod
    def _binary(
        condition: bool,
    ) -> float:

        return 1.0 if condition else 0.0

    @staticmethod
    def _count_outgoing(
        edges: list[CodeGraphEdge],
        edge_type: CodeGraphEdgeType,
    ) -> int:

        return sum(
            edge.edge_type == edge_type
            for edge in edges
        )

    @staticmethod
    def _count_incident(
        incoming_edges: list[CodeGraphEdge],
        outgoing_edges: list[CodeGraphEdge],
        edge_type: CodeGraphEdgeType,
    ) -> int:

        incoming = sum(
            edge.edge_type == edge_type
            for edge in incoming_edges
        )

        outgoing = sum(
            edge.edge_type == edge_type
            for edge in outgoing_edges
        )

        return incoming + outgoing