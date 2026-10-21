from __future__ import annotations

import torch
import torch.nn.functional as F

from torch import nn
from torch_geometric.nn import GCNConv


class CodeRiskGNN(nn.Module):
    """
    Graph Convolutional Network for node-level static-risk classification.

    Input:
        x:          [num_nodes, 23]
        edge_index: [2, num_edges]

    Output:
        logits:     [num_nodes, 4]

    Classes:
        0 = LOW
        1 = MEDIUM
        2 = HIGH
        3 = CRITICAL
    """

    def __init__(
        self,
        input_features: int = 23,
        hidden_features: int = 32,
        num_classes: int = 4,
        dropout: float = 0.3,
    ):
        super().__init__()

        self.input_features = input_features
        self.hidden_features = hidden_features
        self.num_classes = num_classes
        self.dropout = dropout

        self.conv1 = GCNConv(
            input_features,
            hidden_features,
        )

        self.conv2 = GCNConv(
            hidden_features,
            hidden_features,
        )

        self.classifier = nn.Linear(
            hidden_features,
            num_classes,
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """
        Return unnormalized class scores for every node.
        """

        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(
            x,
            p=self.dropout,
            training=self.training,
        )

        x = self.conv2(x, edge_index)
        x = F.relu(x)

        logits = self.classifier(x)

        return logits