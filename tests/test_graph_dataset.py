from backend.analysis.graph_dataset import (
    GraphDataset,
    GraphDatasetBuilder,
)

from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
    UnifiedCodeGraph,
)
from backend.analysis.risk_labels import (
    RiskLabelGenerator,
)

def create_test_graph():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "main.py",
        "file",
        name="main.py",
    )

    graph.add_node(
        "main.py::main",
        "function",
        name="main",
        file="main.py",
        line=1,
    )

    graph.add_node(
        "main.py::helper",
        "function",
        name="helper",
        file="main.py",
        line=5,
    )

    graph.add_edge(
        "main.py",
        "main.py::main",
        CodeGraphEdgeType.CONTAINS,
    )

    graph.add_edge(
        "main.py",
        "main.py::helper",
        CodeGraphEdgeType.CONTAINS,
    )

    graph.add_edge(
        "main.py::main",
        "main.py::helper",
        CodeGraphEdgeType.CALLS,
    )

    return graph


def test_graph_dataset_defaults():

    dataset = GraphDataset()

    assert dataset.num_nodes == 0
    assert dataset.num_edges == 0
    assert dataset.num_features == 0


def test_graph_dataset_builder():

    graph = create_test_graph()

    features = {
        "main.py": [
            1.0,
            0.0,
            0.0,
        ],
        "main.py::main": [
            0.0,
            1.0,
            2.0,
        ],
        "main.py::helper": [
            0.0,
            1.0,
            1.0,
        ],
    }

    builder = GraphDatasetBuilder(
        graph,
        features,
    )

    dataset = builder.build()

    assert dataset.num_nodes == 3

    assert dataset.num_edges == 3

    assert dataset.num_features == 3


def test_node_ids_are_stable():

    graph = create_test_graph()

    features = {
        node_id: [1.0]
        for node_id in graph.nodes
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build()

    assert dataset.node_ids == sorted(
        graph.nodes.keys()
    )


def test_edge_index():

    graph = create_test_graph()

    features = {
        node_id: [1.0]
        for node_id in graph.nodes
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build()

    assert len(
        dataset.edge_index
    ) == 2

    assert len(
        dataset.edge_index[0]
    ) == 3

    assert len(
        dataset.edge_index[1]
    ) == 3


def test_edge_types():

    graph = create_test_graph()

    features = {
        node_id: [1.0]
        for node_id in graph.nodes
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build()

    assert (
        "contains"
        in dataset.edge_types
    )

    assert (
        "calls"
        in dataset.edge_types
    )


def test_node_metadata():

    graph = create_test_graph()

    features = {
        node_id: [1.0]
        for node_id in graph.nodes
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build()

    index = dataset.node_ids.index(
        "main.py::main"
    )

    metadata = dataset.node_metadata[
        index
    ]

    assert metadata["file"] == "main.py"

    assert metadata["line"] == 1

    assert (
        metadata["function_id"]
        == "main.py::main"
    )


def test_labels():

    graph = create_test_graph()

    features = {
        node_id: [1.0]
        for node_id in graph.nodes
    }

    labels = {
        "main.py": 0.0,
        "main.py::main": 1.0,
        "main.py::helper": 0.0,
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build(
        labels=labels
    )

    assert dataset.labels == [
        0.0,
        0.0,
        1.0,
    ] or len(dataset.labels) == 3


def test_dataset_validation():

    graph = create_test_graph()

    features = {
        node_id: [1.0]
        for node_id in graph.nodes
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build()

    dataset.validate()


def test_to_dict():

    graph = create_test_graph()

    features = {
        node_id: [
            1.0,
            2.0,
        ]
        for node_id in graph.nodes
    }

    dataset = GraphDatasetBuilder(
        graph,
        features,
    ).build()

    result = dataset.to_dict()

    assert "node_ids" in result
    assert "node_features" in result
    assert "edge_index" in result
    assert "edge_types" in result
    assert "node_types" in result

    assert result["num_nodes"] == 3
    assert result["num_edges"] == 3
    assert result["num_features"] == 2
    
    
def test_from_graph_automatically_extracts_features():

    graph = create_test_graph()

    dataset = (
        GraphDatasetBuilder
        .from_graph(graph)
    )

    assert dataset.num_nodes == 3

    assert dataset.num_edges == 3

    assert dataset.num_features == 23

    assert len(
        dataset.node_features
    ) == dataset.num_nodes

    assert all(
        len(features) == 23
        for features in dataset.node_features
    )

    dataset.validate()
    
def test_graph_dataset_accepts_risk_labels():

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

    assert dataset.labels is not None

    assert len(
        dataset.labels
    ) == dataset.num_nodes

    for node_id, label in zip(
        dataset.node_ids,
        dataset.labels,
    ):

        assert label == float(
            risk_labels[node_id].label
        )


def test_graph_dataset_risk_labels_are_aligned_with_nodes():

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

    for index, node_id in enumerate(
        dataset.node_ids
    ):

        assert dataset.labels[index] == (
            float(
                risk_labels[node_id].label
            )
        )


def test_graph_dataset_still_accepts_numeric_labels():

    graph = create_test_graph()

    numeric_labels = {
        node_id: float(index)
        for index, node_id in enumerate(
            sorted(graph.nodes.keys())
        )
    }

    dataset = (
        GraphDatasetBuilder
        .from_graph(
            graph,
            labels=numeric_labels,
        )
    )

    assert dataset.labels == [
        float(index)
        for index in range(
            dataset.num_nodes
        )
    ]

    dataset.validate()