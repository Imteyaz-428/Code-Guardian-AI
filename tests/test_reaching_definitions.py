import ast
import sys
from pathlib import Path

# Make the project root importable when pytest runs.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.analysis.cfg import CFGAnalyzer
from backend.analysis.data_flow import DataFlowAnalyzer
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsAnalyzer,
)


def analyze_function(source: str, function_name: str = "test"):
    """
    Parse a function, build its CFG, run Data Flow Analysis,
    and then run Reaching Definitions Analysis.
    """

    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )

    # --------------------------------------------------------------
    # Build CFG
    # --------------------------------------------------------------

    cfg = CFGAnalyzer().analyze(function_node)

    # --------------------------------------------------------------
    # Build mapping:
    #
    # source line -> CFG node IDs
    # --------------------------------------------------------------

    cfg_node_map = {}

    for node in cfg.get_nodes():
        if node.line is not None:
            cfg_node_map.setdefault(
                node.line,
                [],
            ).append(node.id)

    # --------------------------------------------------------------
    # First-level Data Flow Analysis
    # --------------------------------------------------------------

    data_flow = DataFlowAnalyzer().analyze(
        function_node=function_node,
        function_id=f"test.py::{function_name}",
        cfg_node_map=cfg_node_map,
    )

    # --------------------------------------------------------------
    # Reaching Definitions
    # --------------------------------------------------------------

    reaching_definitions = ReachingDefinitionsAnalyzer().analyze(
        cfg=cfg,
        data_flow=data_flow,
    )

    return (
        cfg,
        data_flow,
        reaching_definitions,
    )



# Helpers



def definition_by_id(result, definition_id):
    """Return a DefinitionRef by its ID."""

    return next(
        definition
        for definition in result.definitions
        if definition.id == definition_id
    )


def definitions_for_node(result, node_id):
    """Return definition IDs reaching the beginning of a node."""

    return result.in_sets.get(node_id, set())


def find_node_by_line(cfg, line):
    """Return CFG nodes associated with a source line."""

    return [
        node
        for node in cfg.get_nodes()
        if node.line == line
    ]



# Basic definition creation



def test_definition_ids_are_created_in_order():
    source = """
def test():
    x = 10
    y = 20
    return x + y
"""

    cfg, data_flow, result = analyze_function(source)

    assert [definition.id for definition in result.definitions] == [
        "D0",
        "D1",
    ]

    assert result.definitions[0].definition.name == "x"
    assert result.definitions[1].definition.name == "y"



# Sequential reaching definitions



def test_sequential_definition_reaches_next_statement():
    source = """
def test():
    x = 10
    y = x + 5
    return y
"""

    cfg, data_flow, result = analyze_function(source)

    # Find the CFG node representing the y assignment.
    y_nodes = find_node_by_line(cfg, 4)

    assert y_nodes

    y_node_id = y_nodes[0].id

    # x definition should reach the y assignment.
    reaching = definitions_for_node(
        result,
        y_node_id,
    )

    assert "D0" in reaching



# Reassignment / KILL



def test_reassignment_kills_previous_definition():
    source = """
def test():
    x = 10
    x = 20
    return x
"""

    cfg, data_flow, result = analyze_function(source)

    assert len(result.definitions) == 2

    first_definition = "D0"
    second_definition = "D1"

    # Find the return node.
    return_nodes = find_node_by_line(cfg, 5)

    assert return_nodes

    return_node_id = return_nodes[0].id

    reaching = definitions_for_node(
        result,
        return_node_id,
    )

    # Only the latest x definition should reach return.
    assert second_definition in reaching
    assert first_definition not in reaching



# Multiple variables



def test_independent_variables_reach_correctly():
    source = """
def test():
    x = 10
    y = 20
    z = x + y
    return z
"""

    cfg, data_flow, result = analyze_function(source)

    z_nodes = find_node_by_line(cfg, 5)

    assert z_nodes

    z_node_id = z_nodes[0].id

    reaching = definitions_for_node(
        result,
        z_node_id,
    )

    # x and y definitions should both reach z assignment.
    assert "D0" in reaching
    assert "D1" in reaching



# Branches



def test_both_branch_definitions_reach_join():
    source = """
def test(condition):
    if condition:
        x = 10
    else:
        x = 20

    return x
"""

    cfg, data_flow, result = analyze_function(source)

    # Definitions:
    #
    # D0 = condition parameter
    # D1 = x in true branch
    # D2 = x in false branch
    #

    assert len(result.definitions) == 3

    return_nodes = find_node_by_line(cfg, 8)

    assert return_nodes

    return_node_id = return_nodes[0].id

    reaching = definitions_for_node(
        result,
        return_node_id,
    )

    # Both possible x definitions must reach return.
    assert "D1" in reaching
    assert "D2" in reaching



# Branch + unrelated variable



def test_branch_preserves_unrelated_definition():
    source = """
def test(condition):
    y = 100

    if condition:
        x = 10
    else:
        x = 20

    return x + y
"""

    cfg, data_flow, result = analyze_function(source)

    # D0 = condition
    # D1 = y
    # D2 = x true branch
    # D3 = x false branch

    return_nodes = find_node_by_line(cfg, 10)

    assert return_nodes

    return_node_id = return_nodes[0].id

    reaching = definitions_for_node(
        result,
        return_node_id,
    )

    assert "D1" in reaching
    assert "D2" in reaching
    assert "D3" in reaching



# Loop



def test_loop_reaches_definition_back_to_loop():
    source = """
def test():
    x = 0

    while x < 10:
        x = x + 1

    return x
"""

    cfg, data_flow, result = analyze_function(source)

    # D0 = x = 0
    # D1 = x = x + 1

    assert len(result.definitions) == 2

    # The loop contains the second definition.
    loop_body_nodes = find_node_by_line(cfg, 6)

    assert loop_body_nodes

    loop_body_node_id = loop_body_nodes[0].id

    reaching = definitions_for_node(
        result,
        loop_body_node_id,
    )

    # The initial x definition reaches the loop body.
    assert "D0" in reaching



# Function parameter



def test_parameter_is_a_reaching_definition():
    source = """
def test(x):
    y = x + 10
    return y
"""

    cfg, data_flow, result = analyze_function(source)

    # D0 = parameter x
    # D1 = y assignment

    assert len(result.definitions) == 2

    y_nodes = find_node_by_line(cfg, 4)

    assert y_nodes

    y_node_id = y_nodes[0].id

    reaching = definitions_for_node(
        result,
        y_node_id,
    )

    assert "D0" in reaching



# Multiple reassignments



def test_only_latest_definition_reaches_after_multiple_reassignments():
    source = """
def test():
    x = 1
    x = 2
    x = 3
    return x
"""

    cfg, data_flow, result = analyze_function(source)

    assert len(result.definitions) == 3

    return_nodes = find_node_by_line(cfg, 6)

    assert return_nodes

    return_node_id = return_nodes[0].id

    reaching = definitions_for_node(
        result,
        return_node_id,
    )

    assert "D2" in reaching
    assert "D0" not in reaching
    assert "D1" not in reaching



# Result serialization



def test_result_can_be_serialized():
    source = """
def test():
    x = 10
    return x
"""

    cfg, data_flow, result = analyze_function(source)

    serialized = result.to_dict()

    assert serialized["function"] == "test"

    assert "definitions" in serialized
    assert "gen" in serialized
    assert "kill" in serialized
    assert "in" in serialized
    assert "out" in serialized

    assert len(serialized["definitions"]) == 1