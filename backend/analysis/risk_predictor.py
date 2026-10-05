"""
Risk Predictor
==============

Converts Code Guardian GNN predictions into source-code-aware
risk predictions.

Pipeline:

    GraphDataset
          ↓
    CodeGuardianGNN
          ↓
    RiskPredictor
          ↓
    NodeRiskPrediction
          ↓
    file / line / function / risk level
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import torch

from backend.analysis.graph_dataset import GraphDataset
from backend.ml.graph_model import (
    CodeGuardianGNN,
    graph_dataset_to_tensors,
)


# ============================================================
# Risk Prediction
# ============================================================


@dataclass
class NodeRiskPrediction:
    """
    Risk prediction for one Unified Code Graph node.
    """

    node_id: str
    file: str | None
    line: int | None
    function_id: str | None

    risk_probability: float
    risk_level: str

    node_type: str | None = None

    # --------------------------------------------------------
    # Serialization
    # --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# Risk Predictor
# ============================================================


class RiskPredictor:
    """
    Runs the trained Code Guardian GNN and converts its output
    into source-code-aware risk predictions.
    """

    RISK_LEVELS = (
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    )

    def __init__(
        self,
        model: CodeGuardianGNN,
        device: str | torch.device = "cpu",
    ):
        self.model = model
        self.device = torch.device(device)

        self.model.to(self.device)
        self.model.eval()

    # ========================================================
    # Probability → Risk Level
    # ========================================================

    @classmethod
    def probability_to_risk_level(
        cls,
        probability: float,
    ) -> str:
        """
        Convert risk probability into a stable risk level.

        Thresholds:

            < 0.25  → LOW
            < 0.50  → MEDIUM
            < 0.75  → HIGH
            >= 0.75 → CRITICAL
        """

        probability = float(
            max(
                0.0,
                min(
                    1.0,
                    probability,
                ),
            )
        )

        if probability < 0.25:
            return "LOW"

        if probability < 0.50:
            return "MEDIUM"

        if probability < 0.75:
            return "HIGH"

        return "CRITICAL"

    # ========================================================
    # Predict
    # ========================================================

    def predict(
        self,
        dataset: GraphDataset,
    ) -> list[NodeRiskPrediction]:
        """
        Generate risk predictions for every node.
        """

        if dataset.num_nodes == 0:
            return []

        dataset.validate()

        if dataset.num_features == 0:
            raise ValueError(
                "Risk prediction requires node features"
            )

        # ----------------------------------------------------
        # Convert dataset to tensors
        # ----------------------------------------------------

        x, edge_index = graph_dataset_to_tensors(
            dataset
        )

        x = x.to(self.device)
        edge_index = edge_index.to(self.device)

        # ----------------------------------------------------
        # Model inference
        # ----------------------------------------------------

        with torch.no_grad():

            output = self.model(
                x,
                edge_index,
            )

        # ----------------------------------------------------
        # Convert model output to probabilities
        # ----------------------------------------------------

        probabilities, risk_levels = (
            self._to_probabilities_and_levels(
                output
            )
        )

        # ----------------------------------------------------
        # Build predictions
        # ----------------------------------------------------

        predictions: list[
            NodeRiskPrediction
        ] = []

        for index, node_id in enumerate(
            dataset.node_ids
        ):

            metadata = dataset.node_metadata[
                index
            ]

            probability = float(
                probabilities[index]
            )

            predictions.append(
                NodeRiskPrediction(
                    node_id=node_id,
                    file=metadata.get(
                        "file"
                    ),
                    line=metadata.get(
                        "line"
                    ),
                    function_id=metadata.get(
                        "function_id"
                    ),
                    risk_probability=probability,
                    risk_level=risk_levels[index],
                    node_type=(
                        dataset.node_types[index]
                    ),
                )
            )

        return predictions

    # ========================================================
    # Output Conversion
    # ========================================================

    @classmethod
    def _to_probabilities_and_levels(
        cls,
        output: torch.Tensor,
    ) -> tuple[torch.Tensor, list[str]]:
        """
        Convert model output into risk probabilities
        and risk levels.

        Supported model outputs:

            [N]
                Binary logits.

            [N, 1]
                Binary logits.

            [N, 2]
                Binary classification logits.

            [N, 4]
                Four-class risk classification:

                    0 -> LOW
                    1 -> MEDIUM
                    2 -> HIGH
                    3 -> CRITICAL
        """

        # ----------------------------------------------------
        # Binary: [N]
        # ----------------------------------------------------

        if output.ndim == 1:

            probabilities = torch.sigmoid(
                output
            )

            levels = [
                cls.probability_to_risk_level(
                    float(probability)
                )
                for probability in probabilities
            ]

            return probabilities, levels

        # ----------------------------------------------------
        # Matrix output
        # ----------------------------------------------------

        if output.ndim == 2:

            num_classes = output.shape[1]

            # ------------------------------------------------
            # Binary: [N, 1]
            # ------------------------------------------------

            if num_classes == 1:

                probabilities = torch.sigmoid(
                    output[:, 0]
                )

                levels = [
                    cls.probability_to_risk_level(
                        float(probability)
                    )
                    for probability in probabilities
                ]

                return probabilities, levels

            # ------------------------------------------------
            # Binary classification: [N, 2]
            # ------------------------------------------------

            if num_classes == 2:

                class_probabilities = torch.softmax(
                    output,
                    dim=1,
                )

                probabilities = (
                    class_probabilities[:, 1]
                )

                levels = [
                    cls.probability_to_risk_level(
                        float(probability)
                    )
                    for probability in probabilities
                ]

                return probabilities, levels

            # ------------------------------------------------
            # Code Guardian 4-class classification
            # ------------------------------------------------

            if num_classes == 4:

                class_probabilities = torch.softmax(
                    output,
                    dim=1,
                )

                predicted_classes = torch.argmax(
                    class_probabilities,
                    dim=1,
                )

                probabilities = (
                    class_probabilities.max(
                        dim=1
                    ).values
                )

                class_to_level = {
                    0: "LOW",
                    1: "MEDIUM",
                    2: "HIGH",
                    3: "CRITICAL",
                }

                levels = [
                    class_to_level[
                        int(predicted_class)
                    ]
                    for predicted_class
                    in predicted_classes
                ]

                return probabilities, levels

        raise ValueError(
            "Unsupported model output shape: "
            f"{tuple(output.shape)}"
        )

    # ========================================================
    # Dictionary Output
    # ========================================================

    def predict_to_dict(
        self,
        dataset: GraphDataset,
    ) -> list[dict[str, Any]]:
        """
        Generate predictions directly as dictionaries.
        """

        return [
            prediction.to_dict()
            for prediction in self.predict(
                dataset
            )
        ]

    # ========================================================
    # Highest Risk Nodes
    # ========================================================

    def highest_risk_nodes(
        self,
        dataset: GraphDataset,
        limit: int = 10,
    ) -> list[NodeRiskPrediction]:
        """
        Return the highest-risk nodes.

        Results are sorted deterministically by:

            1. risk probability descending
            2. node ID ascending
        """

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero"
            )

        predictions = self.predict(
            dataset
        )

        predictions.sort(
            key=lambda prediction: (
                -prediction.risk_probability,
                prediction.node_id,
            )
        )

        return predictions[:limit]