import torch

from backend.analysis.graph_dataset import (
    GraphDataset,
)
from backend.analysis.risk_predictor import (
    NodeRiskPrediction,
    RiskPredictor,
)
from backend.ml.graph_model import (
    CodeGuardianGNN,
)


# ============================================================
# Helpers
# ============================================================


def create_dataset():
    return GraphDataset(
        node_ids=[
            "main.py::safe",
            "main.py::risky",
            "utils.py::helper",
        ],
        node_features=[
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
        edge_index=[
            [0, 1],
            [1, 2],
        ],
        edge_types=[
            "calls",
            "contains",
        ],
        node_types=[
            "function",
            "function",
            "function",
        ],
        node_metadata=[
            {
                "id": "main.py::safe",
                "name": "safe",
                "file": "main.py",
                "line": 1,
                "function_id": "main.py::safe",
            },
            {
                "id": "main.py::risky",
                "name": "risky",
                "file": "main.py",
                "line": 10,
                "function_id": "main.py::risky",
            },
            {
                "id": "utils.py::helper",
                "name": "helper",
                "file": "utils.py",
                "line": 5,
                "function_id": "utils.py::helper",
            },
        ],
    )


def create_model():
    torch.manual_seed(42)

    return CodeGuardianGNN(
        input_dim=3,
    )


# ============================================================
# Tests
# ============================================================


def test_probability_to_risk_level():
    assert (
        RiskPredictor.probability_to_risk_level(
            0.10
        )
        == "LOW"
    )

    assert (
        RiskPredictor.probability_to_risk_level(
            0.30
        )
        == "MEDIUM"
    )

    assert (
        RiskPredictor.probability_to_risk_level(
            0.60
        )
        == "HIGH"
    )

    assert (
        RiskPredictor.probability_to_risk_level(
            0.90
        )
        == "CRITICAL"
    )


def test_probability_is_clamped():
    assert (
        RiskPredictor.probability_to_risk_level(
            -1.0
        )
        == "LOW"
    )

    assert (
        RiskPredictor.probability_to_risk_level(
            2.0
        )
        == "CRITICAL"
    )


def test_predictor_initialization():
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    assert predictor.model is model
    assert predictor.device.type == "cpu"


def test_predict_returns_prediction_for_every_node():
    dataset = create_dataset()
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    predictions = predictor.predict(
        dataset
    )

    assert len(predictions) == dataset.num_nodes


def test_prediction_metadata_is_preserved():
    dataset = create_dataset()
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    predictions = predictor.predict(
        dataset
    )

    prediction = predictions[0]

    assert prediction.node_id == (
        "main.py::safe"
    )

    assert prediction.file == "main.py"
    assert prediction.line == 1

    assert prediction.function_id == (
        "main.py::safe"
    )

    assert prediction.node_type == (
        "function"
    )


def test_prediction_probability_is_valid():
    dataset = create_dataset()
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    predictions = predictor.predict(
        dataset
    )

    for prediction in predictions:

        assert (
            0.0
            <= prediction.risk_probability
            <= 1.0
        )

        assert (
            prediction.risk_level
            in RiskPredictor.RISK_LEVELS
        )


def test_prediction_to_dict():
    prediction = NodeRiskPrediction(
        node_id="main.py::main",
        file="main.py",
        line=10,
        function_id="main.py::main",
        risk_probability=0.85,
        risk_level="CRITICAL",
        node_type="function",
    )

    result = prediction.to_dict()

    assert result["node_id"] == (
        "main.py::main"
    )

    assert result["file"] == "main.py"
    assert result["line"] == 10
    assert result["function_id"] == (
        "main.py::main"
    )

    assert result["risk_probability"] == 0.85
    assert result["risk_level"] == "CRITICAL"


def test_predict_to_dict():
    dataset = create_dataset()
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    result = predictor.predict_to_dict(
        dataset
    )

    assert len(result) == 3

    assert isinstance(
        result[0],
        dict,
    )

    assert "node_id" in result[0]
    assert "risk_probability" in result[0]
    assert "risk_level" in result[0]


def test_highest_risk_nodes():
    dataset = create_dataset()
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    predictions = predictor.highest_risk_nodes(
        dataset,
        limit=2,
    )

    assert len(predictions) == 2

    assert (
        predictions[0].risk_probability
        >= predictions[1].risk_probability
    )


def test_highest_risk_nodes_rejects_invalid_limit():
    dataset = create_dataset()
    model = create_model()

    predictor = RiskPredictor(
        model
    )

    try:
        predictor.highest_risk_nodes(
            dataset,
            limit=0,
        )
        assert False
    except ValueError as exc:
        assert (
            str(exc)
            == "limit must be greater than zero"
        )


def test_empty_graph_returns_empty_predictions():
    dataset = GraphDataset()

    model = create_model()

    predictor = RiskPredictor(
        model
    )

    predictions = predictor.predict(
        dataset
    )

    assert predictions == []