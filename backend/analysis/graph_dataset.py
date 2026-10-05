"""
Graph Dataset
=============

Framework-independent representation of the Unified Code Graph.

This module converts:

    UnifiedCodeGraph
          +
    Graph Features
          ↓
    GraphDataset

The output is intentionally independent of PyTorch,
PyTorch Geometric, TensorFlow, etc.

Later this can be converted into:

    PyTorch Geometric Data
    DGL Graph
    NetworkX
    custom GNN input

without changing the analysis layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.analysis.unified_code_graph import (
    CodeGraphEdge,
    UnifiedCodeGraph,
)
from backend.analysis.risk_labels import RiskLabel


# ============================================================
# Graph Dataset
# ============================================================


@dataclass
class GraphDataset:
    """
    ML-ready representation of a Code Guardian graph.

    Attributes
    ----------
    node_ids:
        Node ID for every row in node_features.

    node_features:
        Numerical feature vectors.

        Example:

            [
                [1.0, 0.0, 3.0],
                [0.0, 1.0, 2.0],
            ]

    edge_index:
        Graph connectivity represented as:

            [
                [source_index_1, source_index_2, ...],
                [target_index_1, target_index_2, ...],
            ]

    edge_types:
        Edge type corresponding to each edge.

    node_types:
        Original node type for every node.

    node_metadata:
        Metadata allowing ML predictions to be mapped
        back to the original source code.

    labels:
        Optional labels for supervised learning.
    """

    node_ids: list[str] = field(
        default_factory=list
    )

    node_features: list[list[float]] = field(
        default_factory=list
    )

    edge_index: list[list[int]] = field(
        default_factory=lambda: [
            [],
            [],
        ]
    )

    edge_types: list[str] = field(
        default_factory=list
    )

    node_types: list[str] = field(
        default_factory=list
    )

    node_metadata: list[dict[str, Any]] = field(
        default_factory=list
    )

    labels: list[float] | None = None

    # --------------------------------------------------------
    # Convenience
    # --------------------------------------------------------

    @property
    def num_nodes(self) -> int:
        return len(self.node_ids)

    @property
    def num_edges(self) -> int:
        return len(self.edge_types)

    @property
    def num_features(self) -> int:

        if not self.node_features:
            return 0

        return len(self.node_features[0])

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def validate(self) -> None:
        """
        Validate internal dataset consistency.
        """

        if len(self.node_ids) != len(
            self.node_features
        ):
            raise ValueError(
                "node_ids and node_features "
                "must have the same length"
            )

        if len(self.node_ids) != len(
            self.node_types
        ):
            raise ValueError(
                "node_ids and node_types "
                "must have the same length"
            )

        if len(self.node_ids) != len(
            self.node_metadata
        ):
            raise ValueError(
                "node_ids and node_metadata "
                "must have the same length"
            )

        if len(self.edge_index) != 2:
            raise ValueError(
                "edge_index must contain "
                "exactly two rows"
            )

        if len(self.edge_index[0]) != len(
            self.edge_index[1]
        ):
            raise ValueError(
                "edge_index source and target "
                "lists must have the same length"
            )

        if len(self.edge_index[0]) != len(
            self.edge_types
        ):
            raise ValueError(
                "edge_types must contain one "
                "entry per edge"
            )

        if self.labels is not None:

            if len(self.labels) != self.num_nodes:

                raise ValueError(
                    "labels must contain "
                    "one label per node"
                )

    # --------------------------------------------------------
    # Serialization
    # --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Convert dataset to a JSON-compatible dictionary.
        """

        return {
            "node_ids": self.node_ids,
            "node_features": self.node_features,
            "edge_index": self.edge_index,
            "edge_types": self.edge_types,
            "node_types": self.node_types,
            "node_metadata": self.node_metadata,
            "labels": self.labels,
            "num_nodes": self.num_nodes,
            "num_edges": self.num_edges,
            "num_features": self.num_features,
        }


# ============================================================
# Graph Dataset Builder
# ============================================================


class GraphDatasetBuilder:
    """
    Converts a UnifiedCodeGraph into GraphDataset.

    The builder expects a feature mapping:

        {
            node_id: [feature_1, feature_2, ...]
        }

    This keeps feature extraction separate from dataset
    construction.
    """

    def __init__(
        self,
        graph: UnifiedCodeGraph,
        features: dict[str, list[float]] | None = None,
    ):

        self.graph = graph

        self.features = features or {}
        
    
    @classmethod
    def from_graph(
        cls,
        graph: UnifiedCodeGraph,
        labels: dict[str, float | int | RiskLabel] | None = None,
    ) -> GraphDataset:
        """
        Build a GraphDataset directly from a UnifiedCodeGraph.

        The method automatically extracts graph features and then
        constructs the ML-ready dataset.

        Pipeline:

            UnifiedCodeGraph
                    ↓
            GraphFeatureExtractor
                    ↓
            GraphDatasetBuilder
                    ↓
            GraphDataset
        """

        from backend.analysis.graph_features import (
            GraphFeatureExtractor,
        )

        feature_extractor = (
            GraphFeatureExtractor(graph)
        )

        features = (
            feature_extractor.extract()
        )

        builder = cls(
            graph=graph,
            features=features,
        )

        return builder.build(
            labels=labels
        )

    # ========================================================
    # Build
    # ========================================================

    def build(
        self,
        labels: dict[str, float | int | RiskLabel] | None = None,
    ) -> GraphDataset:

        dataset = GraphDataset()

        # ----------------------------------------------------
        # Stable node ordering
        # ----------------------------------------------------

        node_ids = sorted(
            self.graph.nodes.keys()
        )

        node_to_index = {
            node_id: index
            for index, node_id in enumerate(
                node_ids
            )
        }

        # ----------------------------------------------------
        # Nodes
        # ----------------------------------------------------

        for node_id in node_ids:

            node = self.graph.nodes[
                node_id
            ]

            dataset.node_ids.append(
                node_id
            )

            # Feature vector

            feature_vector = self.features.get(
                node_id,
                [],
            )

            dataset.node_features.append(
                [
                    float(value)
                    for value in feature_vector
                ]
            )

            dataset.node_types.append(
                node.node_type
            )

            function_id = node.function_id

            if (
                function_id is None
                and node.node_type in {
                    "function",
                    "method",
                }
            ):
                function_id = node.id

            metadata = {
                "id": node.id,
                "name": node.name,
                "file": node.file,
                "line": node.line,
                "function_id": function_id,
            }

            metadata.update(
                node.metadata
            )

            dataset.node_metadata.append(
                metadata
            )

        # ----------------------------------------------------
        # Edges
        # ----------------------------------------------------

        for edge in self.graph.edges:

            source_index = node_to_index.get(
                edge.source
            )

            target_index = node_to_index.get(
                edge.target
            )

            if (
                source_index is None
                or target_index is None
            ):
                continue

            dataset.edge_index[0].append(
                source_index
            )

            dataset.edge_index[1].append(
                target_index
            )

            dataset.edge_types.append(
                edge.edge_type.value
            )

        # --------------------------------------------------------
        # Labels
        # --------------------------------------------------------

        if labels is not None:

            dataset.labels = []

            for node_id in node_ids:

                label = labels.get(
                    node_id,
                    0.0,
                )

                # RiskLabel object
                if isinstance(
                    label,
                    RiskLabel,
                ):
                    dataset.labels.append(
                        float(label.label)
                    )

                # Numeric label
                else:
                    dataset.labels.append(
                        float(label)
                    )
        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        dataset.validate()

        return dataset