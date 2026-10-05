from backend.analysis.risk_labels import (
    RiskLabelGenerator,
    RiskLevel,
)

from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
    UnifiedCodeGraph,
)


def create_risk_graph():

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
        "main.py::risky",
        "function",
        name="risky",
        file="main.py",
        line=10,
        function_id="main.py::risky",
    )

    graph.add_node(
        "main.py::source",
        "use",
        name="source",
        file="main.py",
        line=13,
        function_id="main.py::risky",
    )

    graph.add_node(
        "main.py::sink",
        "use",
        name="sink",
        file="main.py",
        line=14,
        function_id="main.py::risky",
    )

    graph.add_node(
        "main.py::data",
        "use",
        name="data",
        file="main.py",
        line=15,
        function_id="main.py::risky",
    )

    # --------------------------------------------------------
    # Taint flow
    # --------------------------------------------------------

    graph.add_edge(
        "main.py::source",
        "main.py::sink",
        CodeGraphEdgeType.TAINT_FLOW,
    )

    # --------------------------------------------------------
    # Data dependency
    # --------------------------------------------------------

    graph.add_edge(
        "main.py::risky",
        "main.py::data",
        CodeGraphEdgeType.DATA_DEPENDENCY,
    )

    return graph


def test_risk_levels_are_stable():

    assert RiskLevel.LOW == 0
    assert RiskLevel.MEDIUM == 1
    assert RiskLevel.HIGH == 2
    assert RiskLevel.CRITICAL == 3


def test_generator_creates_label_for_every_node():

    graph = create_risk_graph()

    labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    assert len(labels) == 5

    assert set(labels.keys()) == set(
        graph.nodes.keys()
    )


def test_safe_node_is_low_risk():

    graph = create_risk_graph()

    labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    safe = labels[
        "main.py::safe"
    ]

    assert safe.level == RiskLevel.LOW

    assert safe.label == 0

    assert safe.score == 0.0

    assert safe.evidence == []


def test_taint_flow_creates_risk():

    graph = create_risk_graph()

    labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    sink = labels[
        "main.py::sink"
    ]

    assert sink.score >= 4.0

    assert sink.level == RiskLevel.HIGH

    assert sink.label == 2

    assert any(
        "Taint-flow"
        in evidence.reason
        for evidence in sink.evidence
    )


def test_data_dependency_creates_risk():

    graph = create_risk_graph()

    labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    data = labels[
        "main.py::data"
    ]

    assert data.score >= 1.5

    assert data.level == RiskLevel.LOW

    assert any(
        "Data dependency"
        in evidence.reason
        for evidence in data.evidence
    )


def test_risk_label_to_dict():

    graph = create_risk_graph()

    labels = (
        RiskLabelGenerator(graph)
        .generate()
    )

    sink = labels[
        "main.py::sink"
    ]

    result = sink.to_dict()

    assert result["node_id"] == (
        "main.py::sink"
    )

    assert result["label"] == 2

    assert result["level"] == "HIGH"

    assert "evidence" in result


def test_risk_generation_is_deterministic():

    graph = create_risk_graph()

    generator = RiskLabelGenerator(
        graph
    )

    first = generator.generate()

    second = generator.generate()

    assert first.keys() == second.keys()

    for node_id in first:

        assert (
            first[node_id].score
            == second[node_id].score
        )

        assert (
            first[node_id].level
            == second[node_id].level
        )