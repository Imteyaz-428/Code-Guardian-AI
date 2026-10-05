from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
    UnifiedCodeGraph,
    UnifiedCodeGraphBuilder,
)


def test_add_node():

    graph = UnifiedCodeGraph()

    graph.add_node(
        node_id="main.py",
        node_type="file",
        name="main.py",
    )

    assert "main.py" in graph.nodes
    assert graph.nodes["main.py"].node_type == "file"


def test_add_edge():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "main.py",
        "file",
    )

    graph.add_node(
        "main.py::main",
        "function",
    )

    graph.add_edge(
        "main.py",
        "main.py::main",
        CodeGraphEdgeType.CONTAINS,
    )

    assert len(graph.edges) == 1

    edge = graph.edges[0]

    assert edge.source == "main.py"
    assert edge.target == "main.py::main"
    assert edge.edge_type == CodeGraphEdgeType.CONTAINS


def test_duplicate_edges_are_ignored():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "a",
        "function",
    )

    graph.add_node(
        "b",
        "function",
    )

    graph.add_edge(
        "a",
        "b",
        CodeGraphEdgeType.CALLS,
    )

    graph.add_edge(
        "a",
        "b",
        CodeGraphEdgeType.CALLS,
    )

    assert len(graph.edges) == 1


def test_function_contains_cfg_node():

    builder = UnifiedCodeGraphBuilder()

    builder.add_function(
        function_id="main.py::main",
        file_path="main.py",
        function_name="main",
        line=1,
    )

    assert "main.py" in builder.graph.nodes

    assert (
        "main.py::main"
        in builder.graph.nodes
    )

    edges = builder.graph.get_edges_by_type(
        CodeGraphEdgeType.CONTAINS
    )

    assert len(edges) == 1

    assert edges[0].source == "main.py"
    assert edges[0].target == "main.py::main"


def test_call_graph():

    builder = UnifiedCodeGraphBuilder()

    builder.add_call_graph(
        {
            "calls": {
                "main.py::main": {
                    "utils.py::helper"
                }
            }
        }
    )

    edges = builder.graph.get_edges_by_type(
        CodeGraphEdgeType.CALLS
    )

    assert len(edges) == 1

    assert edges[0].source == "main.py::main"
    assert edges[0].target == "utils.py::helper"


def test_dependency_graph():

    builder = UnifiedCodeGraphBuilder()

    dependency_graph = {
        "nodes": [
            {
                "id": "main.py",
                "type": "file",
                "file": "main.py",
            },
            {
                "id": "utils.py",
                "type": "file",
                "file": "utils.py",
            },
        ],
        "edges": [
            {
                "source": "main.py",
                "target": "utils.py",
                "type": "import",
            }
        ],
    }

    builder.add_dependency_graph(
        dependency_graph
    )

    edges = builder.graph.get_edges_by_type(
        CodeGraphEdgeType.DEPENDS_ON
    )

    assert len(edges) == 1

    assert edges[0].source == "main.py"
    assert edges[0].target == "utils.py"


def test_def_use():

    builder = UnifiedCodeGraphBuilder()

    builder.add_function(
        "main.py::main",
        file_path="main.py",
        function_name="main",
    )

    result = {
        "chains": [
            {
                "definition_id": "D0",
                "use_id": "U0",
                "variable": "x",
                "definition_line": 2,
                "use_line": 3,
                "definition_kind": "assignment",
                "use_context": "expression",
            }
        ]
    }

    builder.add_def_use(
        "main.py::main",
        result,
    )

    edges = builder.graph.get_edges_by_type(
        CodeGraphEdgeType.DEF_USE
    )

    assert len(edges) == 1

    edge = edges[0]

    assert (
        edge.source
        == "main.py::main::definition::D0"
    )

    assert (
        edge.target
        == "main.py::main::use::U0"
    )


def test_statistics():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "main.py",
        "file",
    )

    graph.add_node(
        "main.py::main",
        "function",
    )

    graph.add_edge(
        "main.py",
        "main.py::main",
        CodeGraphEdgeType.CONTAINS,
    )

    stats = graph.get_statistics()

    assert stats["nodes"] == 2
    assert stats["edges"] == 1

    assert (
        stats["node_types"]["file"]
        == 1
    )

    assert (
        stats["node_types"]["function"]
        == 1
    )

    assert (
        stats["edge_types"]["contains"]
        == 1
    )


def test_to_dict():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "main.py",
        "file",
    )

    result = graph.to_dict()

    assert "nodes" in result
    assert "edges" in result
    assert "statistics" in result
    
    
def test_use_before_definition_relationship():
    builder = UnifiedCodeGraphBuilder()

    function_id = "test.py::test"

    builder.add_function(
        function_id=function_id,
        file_path="test.py",
        function_name="test",
        line=1,
    )

    # Existing variable-use node.
    builder.add_data_flow(
        function_id,
        {
            "uses": [
                {
                    "name": "x",
                    "line": 2,
                    "context": "load",
                }
            ]
        },
    )

    # UBD finding referring to the same use.
    builder.add_use_before_definition(
        function_id,
        {
            "findings": [
                {
                    "variable": "x",
                    "line": 2,
                    "use_id": "U0",
                    "reason": "Variable is used before a definition reaches this point.",
                    "cfg_node_ids": [1],
                }
            ]
        },
    )

    graph = builder.graph

    use_node = f"{function_id}::use::U0"
    ubd_node = f"{function_id}::use_before_definition::U0"

    assert use_node in graph.nodes
    assert ubd_node in graph.nodes

    edges = graph.get_edges_by_type(
        CodeGraphEdgeType.USE_BEFORE_DEFINITION
    )

    assert len(edges) == 1
    assert edges[0].source == use_node
    assert edges[0].target == ubd_node
    
    
def test_dead_definition_relationship():
    builder = UnifiedCodeGraphBuilder()

    function_id = "test.py::test"

    builder.add_function(
        function_id=function_id,
        file_path="test.py",
        function_name="test",
        line=1,
    )

    # Existing definition node.
    builder.add_data_flow(
        function_id,
        {
            "definitions": [
                {
                    "name": "x",
                    "line": 2,
                    "id": "D0",
                    "kind": "assignment",
                }
            ]
        },
    )

    # Dead-definition finding referring to D0.
    builder.add_dead_definitions(
        function_id,
        {
            "findings": [
                {
                    "definition_id": "D0",
                    "variable": "x",
                    "line": 2,
                    "definition_kind": "assignment",
                    "reason": (
                        "Definition is never used by any valid data-flow use."
                    ),
                    "cfg_node_ids": [1],
                }
            ]
        },
    )

    graph = builder.graph

    definition_node = (
        f"{function_id}::definition::D0"
    )

    dead_node = (
        f"{function_id}::dead_definition::D0"
    )

    assert definition_node in graph.nodes
    assert dead_node in graph.nodes

    edges = graph.get_edges_by_type(
        CodeGraphEdgeType.DEAD_DEFINITION
    )

    assert len(edges) == 1

    assert edges[0].source == definition_node
    assert edges[0].target == dead_node