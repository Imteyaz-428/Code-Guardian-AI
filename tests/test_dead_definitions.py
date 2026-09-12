import ast

from backend.analysis.cfg import CFGAnalyzer
from backend.analysis.data_flow import DataFlowAnalyzer
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsAnalyzer,
)
from backend.analysis.def_use import DefUseAnalyzer
from backend.analysis.dead_definitions import (
    DeadDefinitionAnalyzer,
)


def analyze_function(source: str, function_name: str = "test"):
    """
    Run the complete analysis pipeline for one function.
    """

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

    # ---------------------------------------------------------
    # CFG
    # ---------------------------------------------------------

    cfg = CFGAnalyzer().analyze(function_node)

    cfg_node_map = {}

    for node in cfg.get_nodes():
        if node.line is not None:
            cfg_node_map.setdefault(
                node.line,
                [],
            ).append(node.id)

    # ---------------------------------------------------------
    # DATA FLOW
    # ---------------------------------------------------------

    data_flow = DataFlowAnalyzer().analyze(
        function_node=function_node,
        function_id=f"test.py::{function_name}",
        cfg_node_map=cfg_node_map,
    )

    # ---------------------------------------------------------
    # REACHING DEFINITIONS
    # ---------------------------------------------------------

    reaching = ReachingDefinitionsAnalyzer().analyze(
        cfg=cfg,
        data_flow=data_flow,
    )

    # ---------------------------------------------------------
    # DEF-USE CHAINS
    # ---------------------------------------------------------

    def_use = DefUseAnalyzer().analyze(
        data_flow=data_flow,
        reaching_definitions=reaching,
    )

    # ---------------------------------------------------------
    # DEAD DEFINITIONS
    # ---------------------------------------------------------

    result = DeadDefinitionAnalyzer().analyze(
        reaching_definitions=reaching,
        def_use=def_use,
    )

    return (
        cfg,
        data_flow,
        reaching,
        def_use,
        result,
    )


def test_unused_local_definition_is_reported():
    source = """
def test():
    x = 10
    y = 20
    return x
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "y"
    assert finding.line == 4


def test_used_definition_is_not_reported():
    source = """
def test():
    x = 10
    return x
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 0


def test_multiple_unused_definitions_are_reported():
    source = """
def test():
    x = 10
    y = 20
    z = 30
    return x
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 2

    variables = {
        finding.variable
        for finding in result.findings
    }

    assert variables == {"y", "z"}


def test_reassigned_definition_before_use_is_reported():
    source = """
def test():
    x = 10
    x = 20
    return x
"""

    _, _, _, _, result = analyze_function(source)

    # The first x definition is overwritten before its value
    # is used.
    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "x"
    assert finding.line == 3


def test_both_reassignments_are_used():
    source = """
def test():
    x = 10
    print(x)

    x = 20
    return x
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 0


def test_definition_used_in_expression_is_not_reported():
    source = """
def test():
    x = 10
    y = x + 5
    return y
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 0


def test_unused_parameter_is_ignored_by_default():
    source = """
def test(x):
    y = 10
    return y
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 0


def test_unused_parameter_can_be_included():
    source = """
def test(x):
    y = 10
    return y
"""

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
        function_id="test.py::test",
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

    result = DeadDefinitionAnalyzer().analyze(
        reaching_definitions=reaching,
        def_use=def_use,
        include_parameters=True,
    )

    variables = {
        finding.variable
        for finding in result.findings
    }

    assert "x" in variables
    assert "y" not in variables


def test_result_can_be_serialized():
    source = """
def test():
    x = 10
    y = 20
    return x
"""

    _, _, _, _, result = analyze_function(source)

    serialized = result.to_dict()

    assert serialized["function"] == "test"
    assert serialized["finding_count"] == 1
    assert len(serialized["findings"]) == 1

    finding = serialized["findings"][0]

    assert finding["variable"] == "y"
    assert finding["line"] == 4


def test_finding_contains_definition_information():
    source = """
def test():
    unused_value = 100
"""

    _, _, _, _, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "unused_value"
    assert finding.definition_kind
    assert finding.definition_id
    assert isinstance(
        finding.cfg_node_ids,
        tuple,
    )
    