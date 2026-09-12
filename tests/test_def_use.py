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
from backend.analysis.def_use import DefUseAnalyzer


def analyze_function(source: str, function_name: str = "test"):
    """
    Run the complete dataflow pipeline for one function:

        AST
         ↓
        CFG
         ↓
        Definitions + Uses
         ↓
        Reaching Definitions
         ↓
        DefUse Chains
    """

    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )

    # 
    # CFG
    # 

    cfg = CFGAnalyzer().analyze(function_node)

    # 
    # Source line → CFG node IDs
    # 

    cfg_node_map = {}

    for node in cfg.get_nodes():
        if node.line is not None:
            cfg_node_map.setdefault(
                node.line,
                [],
            ).append(node.id)

    # 
    # Definitions + Uses
    # 

    data_flow = DataFlowAnalyzer().analyze(
        function_node=function_node,
        function_id=f"test.py::{function_name}",
        cfg_node_map=cfg_node_map,
    )

    # 
    # Reaching Definitions
    # 

    reaching_definitions = ReachingDefinitionsAnalyzer().analyze(
        cfg=cfg,
        data_flow=data_flow,
    )

    # 
    # DefUse Chains
    # 

    def_use = DefUseAnalyzer().analyze(
        data_flow=data_flow,
        reaching_definitions=reaching_definitions,
    )

    return (
        cfg,
        data_flow,
        reaching_definitions,
        def_use,
    )



# Helpers



def chains_for_variable(result, variable):
    """Return all chains involving a variable."""

    return [
        chain
        for chain in result.chains
        if chain.variable == variable
    ]


def chain_pairs(result):
    """Return (definition_id, use_id) pairs."""

    return {
        (
            chain.definition_id,
            chain.use_id,
        )
        for chain in result.chains
    }



# Sequential flow



def test_sequential_definition_use():
    source = """
def test():
    x = 10
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = chains_for_variable(result, "x")

    assert len(chains) == 1

    chain = chains[0]

    assert chain.definition_id == "D0"
    assert chain.use_id == "U0"
    assert chain.variable == "x"
    assert chain.definition_line == 3
    assert chain.use_line == 4



# Multiple variables



def test_multiple_variables_create_independent_chains():
    source = """
def test():
    x = 10
    y = 20
    print(x)
    print(y)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    x_chains = chains_for_variable(result, "x")
    y_chains = chains_for_variable(result, "y")

    assert len(x_chains) == 1
    assert len(y_chains) == 1

    assert x_chains[0].definition_id == "D0"
    assert y_chains[0].definition_id == "D1"



# Reassignment



def test_reassignment_connects_only_latest_definition():
    source = """
def test():
    x = 10
    x = 20
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = chains_for_variable(result, "x")

    assert len(chains) == 1

    chain = chains[0]

    # D0 is killed by D1.
    assert chain.definition_id == "D1"



# Branches



def test_branch_creates_multiple_possible_def_use_chains():
    source = """
def test(condition):
    if condition:
        x = 10
    else:
        x = 20

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = chains_for_variable(result, "x")

    # Both branch definitions can reach print(x).
    assert len(chains) == 2

    definition_ids = {
        chain.definition_id
        for chain in chains
    }

    assert definition_ids == {"D1", "D2"}



# Unrelated definitions must not connect



def test_unrelated_variable_does_not_create_chain():
    source = """
def test():
    x = 10
    y = 20
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    x_chains = chains_for_variable(result, "x")
    y_chains = chains_for_variable(result, "y")

    assert len(x_chains) == 1
    assert len(y_chains) == 0



# Parameter flow



def test_parameter_definition_reaches_use():
    source = """
def test(x):
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = chains_for_variable(result, "x")

    assert len(chains) == 1

    chain = chains[0]

    assert chain.definition_id == "D0"
    assert chain.definition_kind == "parameter"



# Assignment result flow



def test_assignment_to_assignment_flow():
    source = """
def test():
    x = 10
    y = x
    z = y
    print(z)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    x_chains = chains_for_variable(result, "x")
    y_chains = chains_for_variable(result, "y")
    z_chains = chains_for_variable(result, "z")

    assert len(x_chains) == 1
    assert len(y_chains) == 1
    assert len(z_chains) == 1

    assert x_chains[0].definition_id == "D0"
    assert y_chains[0].definition_id == "D1"
    assert z_chains[0].definition_id == "D2"



# Loop



def test_loop_creates_definition_use_chain():
    source = """
def test():
    x = 0

    while x < 10:
        x = x + 1

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = chains_for_variable(result, "x")

    assert chains

    definition_ids = {
        chain.definition_id
        for chain in chains
    }

    # Both the initial and loop definitions can potentially
    # reach different uses of x.
    assert "D0" in definition_ids
    assert "D1" in definition_ids



# Use IDs



def test_each_use_gets_unique_use_id():
    source = """
def test():
    x = 10
    print(x)
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    x_chains = chains_for_variable(result, "x")

    use_ids = {
        chain.use_id
        for chain in x_chains
    }

    assert len(use_ids) == 2
    assert use_ids == {"U0", "U1"}



# Query helpers



def test_get_chains_for_definition():
    source = """
def test():
    x = 10
    print(x)
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = result.get_chains_for_definition("D0")

    assert len(chains) == 2

    assert {
        chain.use_id
        for chain in chains
    } == {"U0", "U1"}


def test_get_chains_for_use():
    source = """
def test(condition):
    if condition:
        x = 10
    else:
        x = 20

    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    chains = result.get_chains_for_use("U1")

    # The x use is reached by both branch definitions.
    assert len(chains) == 2

    assert {
        chain.definition_id
        for chain in chains
    } == {"D1", "D2"}



# Serialization



def test_def_use_result_can_be_serialized():
    source = """
def test():
    x = 10
    print(x)
"""

    cfg, data_flow, reaching, result = analyze_function(source)

    serialized = result.to_dict()

    assert serialized["function"] == "test"
    assert "chains" in serialized
    assert len(serialized["chains"]) == 1

    chain = serialized["chains"][0]

    assert chain["definition_id"] == "D0"
    assert chain["use_id"] == "U0"
    assert chain["variable"] == "x"