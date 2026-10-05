from backend.analysis.graph_features import (
    GraphFeatureExtractor,
    GraphFeatureSchema,
)

from backend.analysis.unified_code_graph import (
    CodeGraphEdgeType,
    UnifiedCodeGraph,
)


def create_graph():

    graph = UnifiedCodeGraph()

    graph.add_node(
        "main.py",
        "file",
        name="main.py",
        file="main.py",
    )

    graph.add_node(
        "main.py::main",
        "function",
        name="main",
        file="main.py",
        line=1,
        function_id="main.py::main",
    )

    graph.add_node(
        "main.py::helper",
        "function",
        name="helper",
        file="main.py",
        line=5,
        function_id="main.py::helper",
    )

    graph.add_node(
        "main.py::cfg::0",
        "cfg_node",
        file="main.py",
        line=1,
        function_id="main.py::main",
    )

    graph.add_node(
        "main.py::definition::D0",
        "definition",
        name="x",
        file="main.py",
        line=2,
        function_id="main.py::main",
    )

    graph.add_node(
        "main.py::use::U0",
        "use",
        name="x",
        file="main.py",
        line=3,
        function_id="main.py::main",
    )

    # File -> functions

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

    # Function -> CFG

    graph.add_edge(
        "main.py::main",
        "main.py::cfg::0",
        CodeGraphEdgeType.HAS_CFG_NODE,
    )

    # Function call

    graph.add_edge(
        "main.py::main",
        "main.py::helper",
        CodeGraphEdgeType.CALLS,
    )

    # Definition / use

    graph.add_edge(
        "main.py::main",
        "main.py::definition::D0",
        CodeGraphEdgeType.DEFINES,
    )

    graph.add_edge(
        "main.py::main",
        "main.py::use::U0",
        CodeGraphEdgeType.USES,
    )

    # Def-use

    graph.add_edge(
        "main.py::definition::D0",
        "main.py::use::U0",
        CodeGraphEdgeType.DEF_USE,
    )

    return graph


def test_feature_schema():

    schema = GraphFeatureSchema()

    assert schema.size == 23

    assert (
        "is_file"
        in schema.names
    )

    assert (
        "is_function"
        in schema.names
    )

    assert (
        "calls_count"
        in schema.names
    )

    assert (
        "def_use_count"
        in schema.names
    )


def test_extract_features():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    features = extractor.extract()

    assert len(features) == 6

    for vector in features.values():

        assert len(vector) == 23


def test_file_features():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    features = extractor.extract()

    vector = features[
        "main.py"
    ]

    names = extractor.feature_names()

    index = names.index(
        "is_file"
    )

    assert vector[index] == 1.0


def test_function_features():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    features = extractor.extract()

    vector = features[
        "main.py::main"
    ]

    names = extractor.feature_names()

    assert vector[
        names.index("is_function")
    ] == 1.0

    assert vector[
        names.index("has_source_location")
    ] == 1.0

    assert vector[
        names.index("has_function_context")
    ] == 1.0


def test_function_relationship_features():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    features = extractor.extract()

    vector = features[
        "main.py::main"
    ]

    names = extractor.feature_names()

    assert vector[
        names.index("contains_count")
    ] == 0.0

    assert vector[
        names.index("cfg_node_count")
    ] == 1.0

    assert vector[
        names.index("calls_count")
    ] == 1.0

    assert vector[
        names.index("defines_count")
    ] == 1.0

    assert vector[
        names.index("uses_count")
    ] == 1.0


def test_def_use_features():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    features = extractor.extract()

    vector = features[
        "main.py::definition::D0"
    ]

    names = extractor.feature_names()

    assert vector[
        names.index("def_use_count")
    ] == 1.0


def test_cfg_features():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    features = extractor.extract()

    vector = features[
        "main.py::cfg::0"
    ]

    names = extractor.feature_names()

    assert vector[
        names.index("is_cfg_node")
    ] == 1.0

    assert vector[
        names.index("has_source_location")
    ] == 1.0


def test_feature_matrix():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    node_ids, matrix = (
        extractor.feature_matrix()
    )

    assert len(node_ids) == 6

    assert len(matrix) == 6

    assert all(
        len(vector) == 23
        for vector in matrix
    )

    assert node_ids == sorted(
        node_ids
    )


def test_feature_names_are_stable():

    graph = create_graph()

    extractor = GraphFeatureExtractor(
        graph
    )

    names = extractor.feature_names()

    assert names == (
        "is_file",
        "is_function",
        "is_method",
        "is_cfg_node",
        "is_definition",
        "is_use",
        "has_source_location",
        "has_function_context",
        "incoming_edge_count",
        "outgoing_edge_count",
        "contains_count",
        "nests_count",
        "cfg_node_count",
        "control_flow_count",
        "calls_count",
        "depends_on_count",
        "defines_count",
        "uses_count",
        "def_use_count",
        "taint_flow_count",
        "data_dependency_count",
        "inherits_count",
        "overrides_count",
    )