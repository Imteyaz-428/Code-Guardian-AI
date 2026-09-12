import ast

from backend.analysis.cfg import CFGAnalyzer
from backend.analysis.data_flow import DataFlowAnalyzer
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsAnalyzer,
)
from backend.analysis.def_use import DefUseAnalyzer
from backend.analysis.taint_analysis import TaintAnalyzer


def analyze_function(
    source: str,
    function_name: str = "test",
    source_names=None,
    sink_names=None,
):
    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
        and node.name == function_name
    )

    cfg = CFGAnalyzer().analyze(function_node)

    cfg_node_map = {}

    for node in cfg.get_nodes():
        if node.line is not None:
            cfg_node_map.setdefault(
                node.line,
                [],
            ).append(node.id)

    data_flow = DataFlowAnalyzer().analyze(
        function_node=function_node,
        function_id=f"test.py::{function_name}",
        cfg_node_map=cfg_node_map,
    )

    reaching = ReachingDefinitionsAnalyzer().analyze(
        cfg=cfg,
        data_flow=data_flow,
    )

    def_use = DefUseAnalyzer().analyze(
        data_flow=data_flow,
        reaching_definitions=reaching,
    )

    result = TaintAnalyzer().analyze(
        function_node=function_node,
        data_flow=data_flow,
        def_use=def_use,
        source_names=source_names,
        sink_names=sink_names,
    )

    return (
        data_flow,
        reaching,
        def_use,
        result,
    )


def test_source_and_sink_are_detected():
    source = """
def test():
    user_input = request_input()
    execute(user_input)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert len(result.sources) == 1
    assert result.sources[0].name == "request_input"

    assert len(result.sinks) == 1
    assert result.sinks[0].name == "execute"


def test_direct_source_to_sink_is_reported():
    source = """
def test():
    user_input = request_input()
    execute(user_input)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.source_name == "request_input"
    assert finding.sink_name == "execute"
    assert finding.variable == "user_input"


def test_non_tainted_variable_is_not_reported():
    source = """
def test():
    value = 10
    execute(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_different_source_is_not_reported():
    source = """
def test():
    value = another_source()
    execute(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_different_sink_is_not_reported():
    source = """
def test():
    value = request_input()
    print(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_custom_source_and_sink_names():
    source = """
def test():
    value = read_untrusted()
    save_to_database(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"read_untrusted"},
        sink_names={"save_to_database"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.source_name == "read_untrusted"
    assert finding.sink_name == "save_to_database"


def test_attribute_source_and_sink_are_detected():
    source = """
def test():
    value = request.get_input()
    database.execute(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"get_input"},
        sink_names={"execute"},
    )

    assert len(result.sources) == 1
    assert result.sources[0].name == "get_input"

    assert len(result.sinks) == 1
    assert result.sinks[0].name == "execute"


def test_source_without_sink_has_no_finding():
    source = """
def test():
    value = request_input()
    print(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert len(result.sources) == 1
    assert len(result.sinks) == 0
    assert result.finding_count == 0


def test_sink_without_source_has_no_finding():
    source = """
def test():
    value = 10
    execute(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert len(result.sources) == 0
    assert len(result.sinks) == 1
    assert result.finding_count == 0


def test_result_can_be_serialized():
    source = """
def test():
    value = request_input()
    execute(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    serialized = result.to_dict()

    assert serialized["function"] == "test"
    assert "sources" in serialized
    assert "sinks" in serialized
    assert "findings" in serialized
    assert serialized["finding_count"] == 1


def test_finding_contains_path():
    source = """
def test():
    value = request_input()
    execute(value)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    finding = result.findings[0]

    assert finding.path == (
        "request_input",
        "value",
        "execute",
    )


def test_multiple_tainted_flows_are_detected():
    source = """
def test():
    first = request_input()
    second = request_input()

    execute(first)
    execute(second)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 2