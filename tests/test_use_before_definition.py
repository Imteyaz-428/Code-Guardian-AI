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
from backend.analysis.use_before_definition import (
    UseBeforeDefinitionAnalyzer,
)


def analyze_function(source: str, function_name: str = "test"):
    """
    Run the complete data-flow pipeline for one function:

        AST
         ↓
        CFG
         ↓
        Definitions + Uses
         ↓
        Reaching Definitions
         ↓
        Use-Before-Definition
    """

    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )

    # --------------------------------------------------------------
    # CFG
    # --------------------------------------------------------------

    cfg = CFGAnalyzer().analyze(function_node)

    # --------------------------------------------------------------
    # Source line → CFG node IDs
    # --------------------------------------------------------------

    cfg_node_map = {}

    for node in cfg.get_nodes():
        if node.line is not None:
            cfg_node_map.setdefault(
                node.line,
                [],
            ).append(node.id)

    # --------------------------------------------------------------
    # Definitions + Uses
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

    # --------------------------------------------------------------
    # Use-Before-Definition
    # --------------------------------------------------------------

    result = UseBeforeDefinitionAnalyzer().analyze(
        data_flow=data_flow,
        reaching_definitions=reaching_definitions,
    )

    return (
        cfg,
        data_flow,
        reaching_definitions,
        result,
    )



# Basic use-before-definition



def test_variable_used_before_definition():
    source = """
def test():
    print(x)
    x = 10
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 1
    assert result.has_findings

    finding = result.findings[0]

    assert finding.variable == "x"
    assert finding.line == 3
    assert finding.use_id == "U1"



# Valid definition before use



def test_variable_defined_before_use_is_not_reported():
    source = """
def test():
    x = 10
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 0
    assert not result.has_findings



# Multiple variables



def test_only_undefined_variable_is_reported():
    source = """
def test():
    x = 10
    print(x)
    print(y)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "y"
    assert finding.line == 5



# Parameter



def test_parameter_is_defined_before_use():
    source = """
def test(x):
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 0



# Parameter + undefined variable



def test_parameter_does_not_hide_other_undefined_variable():
    source = """
def test(x):
    print(x)
    print(y)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "y"



# Reassignment



def test_reassignment_is_not_reported():
    source = """
def test():
    x = 10
    x = 20
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 0



# Branch: definition on every path



def test_variable_defined_on_both_branch_paths_is_not_reported():
    source = """
def test(condition):
    if condition:
        x = 10
    else:
        x = 20

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 0



# Branch: definition on only one path



def test_variable_defined_on_only_one_branch_is_reported():
    source = """
def test(condition):
    if condition:
        x = 10

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "x"



# Loop



def test_variable_defined_before_loop_is_not_reported():
    source = """
def test():
    x = 0

    while x < 10:
        x = x + 1

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 0



# Loop-only definition



def test_variable_defined_only_inside_loop_is_reported_after_loop():
    source = """
def test(condition):
    while condition:
        x = 10
        break

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "x"



# Multiple undefined variables



def test_multiple_undefined_variables_are_reported():
    source = """
def test():
    print(x)
    print(y)
    print(z)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 3

    variables = {
        finding.variable
        for finding in result.findings
    }

    assert variables == {"x", "y", "z"}



# Serialization



def test_result_can_be_serialized():
    source = """
def test():
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    serialized = result.to_dict()

    assert serialized["function"] == "test"
    assert "findings" in serialized
    assert len(serialized["findings"]) == 1

    finding = serialized["findings"][0]

    assert finding["variable"] == "x"
    assert finding["line"] == 3
    assert "reason" in finding



# Finding properties



def test_finding_contains_cfg_information():
    source = """
def test():
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.cfg_node_ids
    assert finding.context == "load"
    assert finding.reason