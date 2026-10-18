from __future__ import annotations

from pathlib import Path
from typing import Any

import torch

from backend.analysis.graph_dataset import GraphDatasetBuilder
from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.ml.gnn_model import CodeRiskGNN
from backend.repository.manager import RepositoryManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "gnn"
    / "code_risk_gnn_sampled_best.pt"
)

DEVICE = torch.device("cpu")

RISK_LABELS = {
    0: "LOW",
    1: "MEDIUM",
    2: "HIGH",
    3: "CRITICAL",
}


class CVEFixesInferenceService:
    """
    Experimental CVEFixes-trained node-level risk classifier.

    The model predicts heuristic static-risk categories.
    Its predictions do not independently confirm vulnerabilities.
    """

    def __init__(
        self,
        checkpoint_path: Path = CHECKPOINT_PATH,
    ) -> None:
        self.checkpoint_path = checkpoint_path
        self.model: CodeRiskGNN | None = None

    def load_model(self) -> None:
        if self.model is not None:
            return

        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(
                f"CVEFixes checkpoint not found: "
                f"{self.checkpoint_path}"
            )

        checkpoint = torch.load(
            self.checkpoint_path,
            map_location=DEVICE,
            weights_only=True,
        )

        input_features = int(checkpoint["input_features"])
        hidden_features = int(checkpoint["hidden_features"])
        num_classes = int(checkpoint["num_classes"])

        if input_features != 23 or num_classes != 4:
            raise ValueError(
                "Unexpected CVEFixes checkpoint configuration: "
                f"input_features={input_features}, "
                f"num_classes={num_classes}. "
                "Expected 23 features and 4 risk classes."
            )

        self.model = CodeRiskGNN(
            input_features=input_features,
            hidden_features=hidden_features,
            num_classes=num_classes,
            dropout=float(checkpoint.get("dropout", 0.3)),
        ).to(DEVICE)

        self.model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        self.model.eval()

    def predict_repository(
        self,
        repository_path: str,
    ) -> dict[str, Any]:
        self.load_model()

        repository = RepositoryManager(repository_path)

        analyzer = ProjectAnalyzer(
            repository.repository_path
        )

        analyzer.analyze()

        if analyzer.unified_code_graph is None:
            raise ValueError(
                "Analysis did not produce a unified code graph."
            )

        graph = GraphDatasetBuilder.from_graph(
            analyzer.unified_code_graph
        )

        graph.validate()

        if graph.num_nodes == 0:
            raise ValueError(
                "The repository produced an empty graph."
            )

        if graph.num_features != 23:
            raise ValueError(
                f"CVEFixes model expects 23 features per node; "
                f"received {graph.num_features}."
            )

        x = torch.tensor(
            graph.node_features,
            dtype=torch.float32,
            device=DEVICE,
        )

        edge_index = torch.tensor(
            graph.edge_index,
            dtype=torch.long,
            device=DEVICE,
        )

        with torch.no_grad():
            node_logits = self.model(x, edge_index)

            # The trained model predicts risk for individual nodes.
            # Average node probabilities to obtain a repository-level
            # summary. This aggregation is experimental.
            node_probabilities = torch.softmax(
                node_logits,
                dim=1,
            )

            probabilities = node_probabilities.mean(dim=0)

            predicted_class = int(
                probabilities.argmax().item()
            )

        return {
            "status": "success",
            "model": "CVEFixesCodeRiskGNN",
            "prediction": {
                "class_id": predicted_class,
                "label": RISK_LABELS[predicted_class],
                "probabilities": {
                    RISK_LABELS[index]: round(
                        float(probabilities[index].item()),
                        4,
                    )
                    for index in range(4)
                },
            },
            "graph": {
                "num_nodes": graph.num_nodes,
                "num_edges": graph.num_edges,
                "num_features": graph.num_features,
            },
            "warning": (
                "Experimental CVEFixes-trained prediction. "
                "Risk labels are heuristic static-risk labels. "
                "Repository-level probabilities are aggregated "
                "from node predictions and are not calibrated "
                "probabilities of a confirmed vulnerability."
            ),
        }
