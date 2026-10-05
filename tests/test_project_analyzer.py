from backend.analysis.project_analyzer import (
    ProjectAnalyzer,
)
from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
)
from backend.analysis.graph_dataset import (
    GraphDatasetBuilder,
)
from backend.analysis.risk_labels import (
    RiskLabel,
    RiskLevel,
)


def test_project_analyzer_analyzes_sample_project():

    repository_path = "tests/sample_project"

    analyzer = ProjectAnalyzer(
        repository_path
    )

    results = analyzer.analyze()

    assert isinstance(
        results,
        list,
    )

    assert len(results) == 3

    assert all(
        result.file_path
        for result in results
    )

    assert any(
        result.functions
        for result in results
    )

    assert any(
        result.metrics
        for result in results
    )


def test_project_analyzer_continues_after_invalid_python(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        "backend.repository.manager.settings.ALLOWED_ANALYSIS_ROOT",
        tmp_path,
    )

    good_file = (
        tmp_path / "good.py"
    )

    broken_file = (
        tmp_path / "broken.py"
    )

    good_file.write_text(
        "def hello():\n"
        "    return 'hello'\n",
        encoding="utf-8",
    )

    broken_file.write_text(
        "def broken(:\n"
        "    pass\n",
        encoding="utf-8",
    )

    analyzer = ProjectAnalyzer(
        tmp_path
    )

    results = analyzer.analyze()

    assert len(results) == 1

    assert (
        results[0].file_path
        == str(good_file)
    )

    assert len(
        analyzer.errors
    ) == 1

    assert (
        "Syntax error"
        in analyzer.errors[0]
    )


def test_project_analyzer_builds_cfgs():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    assert (
        isinstance(
            analyzer.control_flow_graphs,
            dict,
        )
    )

    assert (
        len(
            analyzer.control_flow_graphs
        ) > 0
    )


def test_project_analyzer_runs_data_flow():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    assert (
        isinstance(
            analyzer.data_flow_results,
            dict,
        )
    )

    assert (
        len(
            analyzer.data_flow_results
        ) > 0
    )


def test_project_analyzer_runs_reaching_definitions():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    assert (
        isinstance(
            analyzer.reaching_definitions,
            dict,
        )
    )

    assert (
        len(
            analyzer.reaching_definitions
        ) > 0
    )


def test_project_analyzer_runs_def_use():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    assert (
        isinstance(
            analyzer.def_use_results,
            dict,
        )
    )

    assert (
        len(
            analyzer.def_use_results
        ) > 0
    )


def test_project_analyzer_runs_use_before_definition():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    assert (
        isinstance(
            analyzer.use_before_definition,
            dict,
        )
    )

    assert (
        len(
            analyzer.use_before_definition
        ) > 0
    )


def test_project_analyzer_runs_dead_definition_analysis():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    assert (
        isinstance(
            analyzer.dead_definitions,
            dict,
        )
    )

    assert (
        len(
            analyzer.dead_definitions
        ) > 0
    )


def test_project_analyzer_builds_unified_code_graph():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    graph = (
        analyzer.unified_code_graph
    )

    assert graph is not None

    assert len(
        graph.nodes
    ) > 0

    assert len(
        graph.edges
    ) > 0


def test_unified_graph_contains_functions():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    graph = (
        analyzer.unified_code_graph
    )

    function_nodes = [
        node
        for node in graph.nodes.values()
        if node.node_type == "function"
    ]

    assert len(
        function_nodes
    ) > 0


def test_unified_graph_contains_cfg_relationships():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    graph = (
        analyzer.unified_code_graph
    )

    cfg_edges = (
        graph.get_edges_by_type(
            CodeGraphEdgeType.HAS_CFG_NODE
        )
    )

    assert len(
        cfg_edges
    ) > 0


def test_unified_graph_contains_call_edges():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    graph = (
        analyzer.unified_code_graph
    )

    call_edges = (
        graph.get_edges_by_type(
            CodeGraphEdgeType.CALLS
        )
    )

    # The sample project contains
    # repository-level function calls.
    assert len(
        call_edges
    ) > 0
    
def test_project_analyzer_produces_ml_ready_dataset():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    graph = (
        analyzer.unified_code_graph
    )

    assert graph is not None

    dataset = (
        GraphDatasetBuilder
        .from_graph(graph)
    )

    assert dataset.num_nodes > 0

    assert dataset.num_edges > 0

    assert dataset.num_features == 23

    assert (
        len(dataset.node_features)
        == dataset.num_nodes
    )

    assert (
        len(dataset.edge_types)
        == dataset.num_edges
    )

    assert (
        len(dataset.node_metadata)
        == dataset.num_nodes
    )

    dataset.validate()
    
    
def test_project_analyzer_generates_risk_labels():

    analyzer = ProjectAnalyzer(
        "tests/sample_project"
    )

    analyzer.analyze()

    labels = (
        analyzer.generate_risk_labels()
    )

    assert labels is not None

    assert isinstance(
        labels,
        dict,
    )

    assert len(labels) > 0

    assert set(labels.keys()) == set(
        analyzer.unified_code_graph.nodes.keys()
    )

    for node_id, risk_label in labels.items():

        assert isinstance(
            node_id,
            str,
        )

        assert isinstance(
            risk_label,
            RiskLabel,
        )

        assert risk_label.node_id == node_id

        assert risk_label.score >= 0

        assert risk_label.level in (
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        )

        assert risk_label.label in (
            0,
            1,
            2,
            3,
        )