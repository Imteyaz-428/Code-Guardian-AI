"""
Code Guardian Graph Risk Model
==============================

A lightweight framework-independent-from-PyG GNN implementation
using PyTorch only.

Input:
    GraphDataset

Output:
    Node-level risk logits.

The model predicts one risk class for every code-graph node:

    0 -> LOW
    1 -> MEDIUM
    2 -> HIGH
    3 -> CRITICAL
"""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

from backend.analysis.graph_dataset import GraphDataset


# ============================================================
# Constants
# ============================================================

NUM_RISK_CLASSES = 4

RISK_LEVELS = (
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
)


# ============================================================
# Graph Convolution Layer
# ============================================================


class GraphConvolution(nn.Module):
    """
    Simple message-passing graph convolution.

    For every node:

        transformed_self
              +
        aggregated_neighbor_messages
              ↓
            output

    This implementation intentionally does not require
    torch_geometric.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
    ) -> None:

        super().__init__()

        self.self_linear = nn.Linear(
            in_features,
            out_features,
        )

        self.neighbor_linear = nn.Linear(
            in_features,
            out_features,
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """
        Parameters
        ----------
        x:
            Node feature matrix.

            Shape:
                [num_nodes, num_features]

        edge_index:
            Graph connectivity.

            Shape:
                [2, num_edges]

        Returns
        -------
        torch.Tensor

            Shape:
                [num_nodes, out_features]
        """

        num_nodes = x.size(0)

        # ----------------------------------------------------
        # No edges
        # ----------------------------------------------------

        if edge_index.numel() == 0:

            return self.self_linear(x)

        # ----------------------------------------------------
        # Source and target indices
        # ----------------------------------------------------

        source = edge_index[0]

        target = edge_index[1]

        # ----------------------------------------------------
        # Gather source-node features
        # ----------------------------------------------------

        messages = x[source]

        # ----------------------------------------------------
        # Aggregate messages
        # ----------------------------------------------------

        aggregated = torch.zeros_like(x)

        aggregated.index_add_(
            0,
            target,
            messages,
        )

        # ----------------------------------------------------
        # Degree normalization
        # ----------------------------------------------------

        degree = torch.zeros(
            num_nodes,
            device=x.device,
            dtype=x.dtype,
        )

        degree.index_add_(
            0,
            target,
            torch.ones(
                target.size(0),
                device=x.device,
                dtype=x.dtype,
            ),
        )

        degree = degree.clamp(
            min=1.0
        ).unsqueeze(1)

        aggregated = (
            aggregated / degree
        )

        # ----------------------------------------------------
        # Transform self + neighbors
        # ----------------------------------------------------

        return (
            self.self_linear(x)
            + self.neighbor_linear(
                aggregated
            )
        )


# ============================================================
# Code Guardian GNN
# ============================================================


class CodeGuardianGNN(nn.Module):
    """
    Node-level risk prediction model.

    Architecture:

        Node Features
             ↓
        GraphConv
             ↓
          ReLU
             ↓
        GraphConv
             ↓
          ReLU
             ↓
        Classifier
             ↓
        Risk Logits

    The model returns logits rather than probabilities.
    CrossEntropyLoss should be used during training.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 64,
        num_classes: int = NUM_RISK_CLASSES,
        dropout: float = 0.2,
    ) -> None:

        super().__init__()

        if input_dim <= 0:
            raise ValueError(
                "input_dim must be greater than zero"
            )

        if hidden_dim <= 0:
            raise ValueError(
                "hidden_dim must be greater than zero"
            )

        if num_classes <= 1:
            raise ValueError(
                "num_classes must be greater than one"
            )

        self.input_dim = input_dim

        self.hidden_dim = hidden_dim

        self.num_classes = num_classes

        self.conv1 = GraphConvolution(
            input_dim,
            hidden_dim,
        )

        self.conv2 = GraphConvolution(
            hidden_dim,
            hidden_dim,
        )

        self.classifier = nn.Linear(
            hidden_dim,
            num_classes,
        )

        self.activation = nn.ReLU()

        self.dropout = nn.Dropout(
            dropout
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """
        Forward pass.

        Parameters
        ----------
        x:
            Node features.

            Shape:
                [N, F]

        edge_index:
            Graph edges.

            Shape:
                [2, E]

        Returns
        -------
        torch.Tensor

            Risk logits.

            Shape:
                [N, num_classes]
        """

        x = self.conv1(
            x,
            edge_index,
        )

        x = self.activation(x)

        x = self.dropout(x)

        x = self.conv2(
            x,
            edge_index,
        )

        x = self.activation(x)

        x = self.dropout(x)

        return self.classifier(x)

    # ========================================================
    # Dataset Conversion
    # ========================================================

    def forward_dataset(
        self,
        dataset: GraphDataset,
    ) -> torch.Tensor:
        """
        Run inference directly from GraphDataset.
        """

        x, edge_index = (
            graph_dataset_to_tensors(
                dataset
            )
        )

        return self.forward(
            x,
            edge_index,
        )


# ============================================================
# Dataset → Tensor Conversion
# ============================================================


def graph_dataset_to_tensors(
    dataset: GraphDataset,
) -> tuple[
    torch.Tensor,
    torch.Tensor,
]:
    """
    Convert GraphDataset into PyTorch tensors.

    Returns:

        x:
            [num_nodes, num_features]

        edge_index:
            [2, num_edges]
    """

    dataset.validate()

    # --------------------------------------------------------
    # Node features
    # --------------------------------------------------------

    if dataset.num_nodes == 0:

        x = torch.empty(
            (0, dataset.num_features),
            dtype=torch.float32,
        )

    else:

        x = torch.tensor(
            dataset.node_features,
            dtype=torch.float32,
        )

    # --------------------------------------------------------
    # Edge index
    # --------------------------------------------------------

    edge_index = torch.tensor(
        dataset.edge_index,
        dtype=torch.long,
    )

    if edge_index.numel() == 0:

        edge_index = torch.empty(
            (2, 0),
            dtype=torch.long,
        )

    return x, edge_index


# ============================================================
# Labels → Tensor
# ============================================================


def graph_dataset_labels_to_tensor(
    dataset: GraphDataset,
) -> torch.Tensor:
    """
    Convert GraphDataset labels into a PyTorch tensor.

    Labels are expected to be integer-like values:

        0 -> LOW
        1 -> MEDIUM
        2 -> HIGH
        3 -> CRITICAL
    """

    dataset.validate()

    if dataset.labels is None:

        raise ValueError(
            "GraphDataset does not contain labels"
        )

    return torch.tensor(
        [
            int(label)
            for label in dataset.labels
        ],
        dtype=torch.long,
    )


# ============================================================
# Prediction Utilities
# ============================================================


def logits_to_predictions(
    logits: torch.Tensor,
) -> torch.Tensor:
    """
    Convert model logits into predicted class IDs.
    """

    if logits.ndim != 2:

        raise ValueError(
            "logits must have shape "
            "[num_nodes, num_classes]"
        )

    return torch.argmax(
        logits,
        dim=1,
    )


def predictions_to_risk_levels(
    predictions: torch.Tensor,
) -> list[str]:
    """
    Convert predicted class IDs into human-readable
    risk levels.
    """

    result: list[str] = []

    for prediction in predictions:

        index = int(
            prediction.item()
        )

        if index < 0 or index >= len(
            RISK_LEVELS
        ):
            raise ValueError(
                f"Invalid risk class: {index}"
            )

        result.append(
            RISK_LEVELS[index]
        )

    return result