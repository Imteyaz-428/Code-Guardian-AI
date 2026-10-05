"""
Code Guardian GNN Trainer
=========================

Training utilities for the CodeGuardianGNN.

Pipeline:

    GraphDataset
        ↓
    Tensor conversion
        ↓
    CodeGuardianGNN
        ↓
    CrossEntropyLoss
        ↓
    Adam optimizer
        ↓
    Trained risk predictor
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from backend.analysis.graph_dataset import GraphDataset

from backend.ml.graph_model import (
    CodeGuardianGNN,
    graph_dataset_labels_to_tensor,
    graph_dataset_to_tensors,
    logits_to_predictions,
)


# ============================================================
# Training Result
# ============================================================


@dataclass
class TrainingResult:
    """
    Summary of a training run.
    """

    epochs: int

    final_loss: float

    final_accuracy: float

    losses: list[float]

    accuracies: list[float]

    def to_dict(self) -> dict:
        return {
            "epochs": self.epochs,
            "final_loss": self.final_loss,
            "final_accuracy": self.final_accuracy,
            "losses": self.losses,
            "accuracies": self.accuracies,
        }


# ============================================================
# Trainer
# ============================================================


class CodeGuardianTrainer:
    """
    Trainer for CodeGuardianGNN.

    Performs full-graph node classification.

        0 -> LOW
        1 -> MEDIUM
        2 -> HIGH
        3 -> CRITICAL
    """

    def __init__(
        self,
        model: CodeGuardianGNN,
        learning_rate: float = 0.001,
        weight_decay: float = 0.0001,
    ) -> None:

        if learning_rate <= 0:
            raise ValueError(
                "learning_rate must be greater than zero"
            )

        if weight_decay < 0:
            raise ValueError(
                "weight_decay cannot be negative"
            )

        self.model = model

        self.learning_rate = learning_rate

        self.weight_decay = weight_decay

        self.criterion = nn.CrossEntropyLoss()

        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )

    # ========================================================
    # Training
    # ========================================================

    def train(
        self,
        dataset: GraphDataset,
        epochs: int = 100,
    ) -> TrainingResult:
        """
        Train the model on one labeled graph.
        """

        if epochs <= 0:
            raise ValueError(
                "epochs must be greater than zero"
            )

        dataset.validate()

        if dataset.num_nodes == 0:
            raise ValueError(
                "Cannot train on an empty graph"
            )

        if dataset.labels is None:
            raise ValueError(
                "Training requires GraphDataset labels"
            )

        x, edge_index = (
            graph_dataset_to_tensors(
                dataset
            )
        )

        labels = (
            graph_dataset_labels_to_tensor(
                dataset
            )
        )

        self.model.train()

        losses: list[float] = []

        accuracies: list[float] = []

        for _ in range(epochs):

            self.optimizer.zero_grad()

            logits = self.model(
                x,
                edge_index,
            )

            loss = self.criterion(
                logits,
                labels,
            )

            loss.backward()

            self.optimizer.step()

            predictions = (
                logits_to_predictions(
                    logits.detach()
                )
            )

            accuracy = (
                predictions == labels
            ).float().mean().item()

            loss_value = loss.item()

            losses.append(
                float(loss_value)
            )

            accuracies.append(
                float(accuracy)
            )

        return TrainingResult(
            epochs=epochs,
            final_loss=losses[-1],
            final_accuracy=accuracies[-1],
            losses=losses,
            accuracies=accuracies,
        )

    # ========================================================
    # Evaluation
    # ========================================================

    def evaluate(
        self,
        dataset: GraphDataset,
    ) -> dict[str, float]:
        """
        Evaluate the model on a labeled graph.
        """

        dataset.validate()

        if dataset.labels is None:
            raise ValueError(
                "Evaluation requires GraphDataset labels"
            )

        if dataset.num_nodes == 0:
            raise ValueError(
                "Cannot evaluate an empty graph"
            )

        x, edge_index = (
            graph_dataset_to_tensors(
                dataset
            )
        )

        labels = (
            graph_dataset_labels_to_tensor(
                dataset
            )
        )

        self.model.eval()

        with torch.no_grad():

            logits = self.model(
                x,
                edge_index,
            )

            loss = self.criterion(
                logits,
                labels,
            )

            predictions = (
                logits_to_predictions(
                    logits
                )
            )

            accuracy = (
                predictions == labels
            ).float().mean().item()

        return {
            "loss": float(
                loss.item()
            ),
            "accuracy": float(
                accuracy
            ),
        }

    # ========================================================
    # Prediction
    # ========================================================

    def predict(
        self,
        dataset: GraphDataset,
    ) -> torch.Tensor:
        """
        Predict risk class for every node.
        """

        dataset.validate()

        if dataset.num_nodes == 0:
            return torch.empty(
                0,
                dtype=torch.long,
            )

        x, edge_index = (
            graph_dataset_to_tensors(
                dataset
            )
        )

        self.model.eval()

        with torch.no_grad():

            logits = self.model(
                x,
                edge_index,
            )

            return logits_to_predictions(
                logits
            )

    # ========================================================
    # Save
    # ========================================================

    def save(
        self,
        path: str | Path,
    ) -> None:
        """
        Save model weights and training configuration.
        """

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        torch.save(
            {
                "model_state_dict":
                    self.model.state_dict(),
                "input_dim":
                    self.model.input_dim,
                "hidden_dim":
                    self.model.hidden_dim,
                "num_classes":
                    self.model.num_classes,
                "learning_rate":
                    self.learning_rate,
                "weight_decay":
                    self.weight_decay,
            },
            path,
        )

    # ========================================================
    # Load
    # ========================================================

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> CodeGuardianTrainer:
        """
        Load a saved CodeGuardian model.
        """

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}"
            )

        checkpoint = torch.load(
            path,
            map_location="cpu",
            weights_only=False,
        )

        model = CodeGuardianGNN(
            input_dim=checkpoint[
                "input_dim"
            ],
            hidden_dim=checkpoint[
                "hidden_dim"
            ],
            num_classes=checkpoint[
                "num_classes"
            ],
        )

        model.load_state_dict(
            checkpoint[
                "model_state_dict"
            ]
        )

        return cls(
            model=model,
            learning_rate=checkpoint.get(
                "learning_rate",
                0.001,
            ),
            weight_decay=checkpoint.get(
                "weight_decay",
                0.0001,
            ),
        )