import pytest

torch = pytest.importorskip("torch")

from backend.analysis.graph_dataset import (
    GraphDatasetBuilder,
)

from backend.analysis.risk_labels import (
    RiskLabelGenerator,
)

from backend.ml.graph_model import (
    CodeGuardianGNN,
    GraphConvolution,
    NUM_RISK_CLASSES,
    RISK_LEVELS,
    graph_dataset_labels_to_tensor,
    graph_dataset_to_tensors,
    logits_to_predictions,
    predictions_to_risk_levels,
)


# ============================================================
# Test Graph
# ============================================================


def create_test_graph():

    from backend.analysis.unified_code_graph import (
        UnifiedCodeGraph,
        CodeGraphEdgeType,
    )

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
        "main.py::sink",
        "use",
        name="sink",
        file="main.py",
        line=15,
        function_id="main.py::process",
    )

    graph.add_edge(
        "main.py::process",
        "main.py::sink",
        CodeGraphEdgeType.DATA_DEPENDENCY,
    )

    return graph


# ============================================================
# Tests
# ============================================================


def test_graph_convolution():

    layer = GraphConvolution(
        in_features=4,
        out_features=8,
    )

    x = torch.randn(
        3,
        4,
    )

    edge_index = torch.tensor(
        [
            [0, 1],
            [1, 2],
        ],
        dtype=torch.long,
    )

    output = layer(
        x,
        edge_index,
    )

    assert output.shape == (
        3,
        8,
    )


def test_graph_dataset_to_tensors():

    graph = create_test_graph()

    dataset = (
        GraphDatasetBuilder
        .from_graph(graph)
    )

    x, edge_index = (
        graph_dataset_to_tensors(
            dataset
        )
    )

    assert isinstance(
        x,
        torch.Tensor,
    )

    assert isinstance(
        edge_index,
        torch.Tensor,
    )

    assert x.shape[0] == (
        dataset.num_nodes
    )

    assert x.shape[1] == (
        dataset.num_features
    )

    assert edge_index.shape[0] == 2

    assert edge_index.shape[1] == (
        dataset.num_edges
    )


def test_graph_dataset_labels_to_tensor():

    graph = create_test_graph()

    risk_labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    dataset = (
        GraphDatasetBuilder
        .from_graph(
            graph,
            labels=risk_labels,
        )
    )

    labels = (
        graph_dataset_labels_to_tensor(
            dataset
        )
    )

    assert labels.dtype == (
        torch.long
    )

    assert labels.shape == (
        dataset.num_nodes,
    )

    assert all(
        0 <= int(label) < NUM_RISK_CLASSES
        for label in labels
    )


def test_code_guardian_gnn_output_shape():

    graph = create_test_graph()

    dataset = (
        GraphDatasetBuilder
        .from_graph(graph)
    )

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
        num_classes=NUM_RISK_CLASSES,
    )

    logits = (
        model.forward_dataset(
            dataset
        )
    )

    assert logits.shape == (
        dataset.num_nodes,
        NUM_RISK_CLASSES,
    )


def test_code_guardian_gnn_predictions():

    graph = create_test_graph()

    dataset = (
        GraphDatasetBuilder
        .from_graph(graph)
    )

    model = CodeGuardianGNN(
        input_dim=dataset.num_features,
        hidden_dim=16,
    )

    logits = (
        model.forward_dataset(
            dataset
        )
    )

    predictions = (
        logits_to_predictions(
            logits
        )
    )

    assert predictions.shape == (
        dataset.num_nodes,
    )

    assert all(
        0 <= int(prediction)
        < NUM_RISK_CLASSES
        for prediction in predictions
    )


def test_predictions_to_risk_levels():

    predictions = torch.tensor(
        [
            0,
            1,
            2,
            3,
        ],
        dtype=torch.long,
    )

    levels = (
        predictions_to_risk_levels(
            predictions
        )
    )

    assert levels == [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]

    assert levels == list(
        RISK_LEVELS
    )


def test_gnn_supports_empty_edges():

    model = CodeGuardianGNN(
        input_dim=4,
        hidden_dim=8,
    )

    x = torch.randn(
        3,
        4,
    )

    edge_index = torch.empty(
        (2, 0),
        dtype=torch.long,
    )

    logits = model(
        x,
        edge_index,
    )

    assert logits.shape == (
        3,
        NUM_RISK_CLASSES,
    )


def test_gnn_is_deterministic_in_eval_mode():

    torch.manual_seed(42)

    model = CodeGuardianGNN(
        input_dim=4,
        hidden_dim=8,
    )

    model.eval()

    x = torch.randn(
        3,
        4,
    )

    edge_index = torch.tensor(
        [
            [0, 1],
            [1, 2],
        ],
        dtype=torch.long,
    )

    output_1 = model(
        x,
        edge_index,
    )

    output_2 = model(
        x,
        edge_index,
    )

    assert torch.allclose(
        output_1,
        output_2,
    )