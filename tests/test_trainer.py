import pytest

torch = pytest.importorskip("torch")

from backend.analysis.graph_dataset import (
    GraphDatasetBuilder,
)

from backend.analysis.risk_labels import (
    RiskLabelGenerator,
)

from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
    UnifiedCodeGraph,
)

from backend.ml.graph_model import (
    CodeGuardianGNN,
    NUM_RISK_CLASSES,
)

from backend.ml.trainer import (
    CodeGuardianTrainer,
    TrainingResult,
)


# ============================================================
# Test Graph
# ============================================================


def create_training_graph():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "main.py::safe",
        "function",
        name="safe",
        file="main.py",
        line=1,
        function_id="main.py::safe",
    )

    graph.add_node(
        "main.py::process",
        "function",
        name="process",
        file="main.py",
        line=10,
        function_id="main.py::process",
    )

    graph.add_node(
        "main.py::source",
        "use",
        name="source",
        file="main.py",
        line=12,
        function_id="main.py::process",
    )

    graph.add_node(
        "main.py::sink",
        "use",
        name="sink",
        file="main.py",
        line=14,
        function_id="main.py::process",
    )

    graph.add_edge(
        "main.py::process",
        "main.py::source",
        CodeGraphEdgeType.DATA_DEPENDENCY,
    )

    graph.add_edge(
        "main.py::source",
        "main.py::sink",
        CodeGraphEdgeType.TAINT_FLOW,
    )

    return graph


def create_training_dataset():

    graph = create_training_graph()

    labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    return (
        GraphDatasetBuilder
        .from_graph(
            graph,
            labels=labels,
        )
    )


# ============================================================
# Tests
# ============================================================


def test_training_result_to_dict():

    result = TrainingResult(
        epochs=3,
        final_loss=0.25,
        final_accuracy=0.75,
        losses=[
            1.0,
            0.5,
            0.25,
        ],
        accuracies=[
            0.25,
            0.50,
            0.75,
        ],
    )

    data = result.to_dict()

    assert data["epochs"] == 3

    assert data["final_loss"] == 0.25

    assert data["final_accuracy"] == 0.75

    assert len(data["losses"]) == 3

    assert len(data["accuracies"]) == 3


def test_trainer_initialization():

    dataset = create_training_dataset()

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
        num_classes=NUM_RISK_CLASSES,
    )

    trainer = CodeGuardianTrainer(
        model,
        learning_rate=0.01,
    )

    assert trainer.model is model

    assert trainer.learning_rate == 0.01


def test_trainer_rejects_invalid_learning_rate():

    dataset = create_training_dataset()

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
    )

    with pytest.raises(
        ValueError,
        match="learning_rate",
    ):
        CodeGuardianTrainer(
            model,
            learning_rate=0,
        )


def test_trainer_requires_labels():

    dataset = create_training_dataset()

    dataset.labels = None

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
    )

    trainer = CodeGuardianTrainer(
        model
    )

    with pytest.raises(
        ValueError,
        match="labels",
    ):
        trainer.train(
            dataset,
            epochs=2,
        )


def test_trainer_trains_model():

    torch.manual_seed(42)

    dataset = create_training_dataset()

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
        num_classes=NUM_RISK_CLASSES,
    )

    trainer = CodeGuardianTrainer(
        model,
        learning_rate=0.01,
    )

    result = trainer.train(
        dataset,
        epochs=5,
    )

    assert isinstance(
        result,
        TrainingResult,
    )

    assert result.epochs == 5

    assert len(
        result.losses
    ) == 5

    assert len(
        result.accuracies
    ) == 5

    assert result.final_loss >= 0

    assert 0.0 <= (
        result.final_accuracy
    ) <= 1.0


def test_trainer_evaluate():

    torch.manual_seed(42)

    dataset = create_training_dataset()

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
    )

    trainer = CodeGuardianTrainer(
        model
    )

    metrics = trainer.evaluate(
        dataset
    )

    assert "loss" in metrics

    assert "accuracy" in metrics

    assert metrics["loss"] >= 0

    assert 0.0 <= metrics[
        "accuracy"
    ] <= 1.0


def test_trainer_predict():

    torch.manual_seed(42)

    dataset = create_training_dataset()

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
    )

    trainer = CodeGuardianTrainer(
        model
    )

    predictions = trainer.predict(
        dataset
    )

    assert predictions.shape == (
        dataset.num_nodes,
    )

    assert predictions.dtype == (
        torch.long
    )

    assert all(
        0 <= int(prediction)
        < NUM_RISK_CLASSES
        for prediction in predictions
    )


def test_trainer_save_and_load(
    tmp_path,
):

    torch.manual_seed(42)

    dataset = create_training_dataset()

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
    )

    trainer = CodeGuardianTrainer(
        model
    )

    trainer.train(
        dataset,
        epochs=2,
    )

    model_path = (
        tmp_path
        / "code_guardian.pt"
    )

    trainer.save(
        model_path
    )

    assert model_path.exists()

    loaded = (
        CodeGuardianTrainer.load(
            model_path
        )
    )

    original_predictions = (
        trainer.predict(dataset)
    )

    loaded_predictions = (
        loaded.predict(dataset)
    )

    assert torch.equal(
        original_predictions,
        loaded_predictions,
    )


def test_trainer_rejects_empty_graph():

    from backend.analysis.graph_dataset import (
        GraphDataset,
    )

    dataset = GraphDataset()

    model = CodeGuardianGNN(
        input_dim=1,
    )

    trainer = CodeGuardianTrainer(
        model
    )

    with pytest.raises(
        ValueError,
        match="empty graph",
    ):
        trainer.train(
            dataset,
            epochs=1,
        )