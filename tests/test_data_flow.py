import ast
import sys
from pathlib import Path

# Make the project root importable when pytest runs from tests/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.analysis.data_flow import DataFlowAnalyzer


def analyze_function(source: str, function_name: str = "test"):
    """Parse source and analyze the requested function."""

    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )

    analyzer = DataFlowAnalyzer()

    return analyzer.analyze(
        function_node=function_node,
        function_id=f"test.py::{function_name}",
    )


def definition_names(result):
    """Return definition names in analysis order."""

    return [definition.name for definition in result.definitions]


def use_names(result):
    """Return use names in analysis order."""

    return [use.name for use in result.uses]


# Parameters


def test_parameter_definition():
    source = """
def test(x, y):
    return x + y
"""

    result = analyze_function(source)

    assert definition_names(result) == ["x", "y"]


def test_parameter_is_also_used():
    source = """
def test(x):
    return x + 10
"""

    result = analyze_function(source)

    assert "x" in definition_names(result)
    assert "x" in use_names(result)


# Assignments


def test_assignment_definition_and_use():
    source = """
def test():
    x = 10
    y = x + 5
    return y
"""

    result = analyze_function(source)

    assert definition_names(result) == ["x", "y"]

    assert use_names(result) == ["x", "y"]


def test_reassignment_creates_multiple_definitions():
    source = """
def test():
    x = 10
    x = 20
    return x
"""

    result = analyze_function(source)

    assert definition_names(result) == ["x", "x"]

    assert use_names(result) == ["x"]


# Branches


def test_if_else_definitions_and_uses():
    source = """
def test(condition):
    if condition:
        x = 10
    else:
        x = 20

    return x
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "condition",
        "x",
        "x",
    ]

    assert use_names(result) == [
        "condition",
        "x",
    ]


def test_branch_local_variables():
    source = """
def test(condition):
    if condition:
        x = 10
        y = x
    else:
        z = 20
        w = z

    return 0
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "condition",
        "x",
        "y",
        "z",
        "w",
    ]

    assert use_names(result) == [
        "condition",
        "x",
        "z",
    ]


# Loops


def test_for_loop_definition_and_use():
    source = """
def test(items):
    total = 0

    for item in items:
        total = total + item

    return total
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "items",
        "total",
        "item",
        "total",
    ]

    assert use_names(result) == [
        "items",
        "total",
        "item",
        "total",
    ]


def test_while_loop_variable_use():
    source = """
def test():
    x = 0

    while x < 10:
        x = x + 1

    return x
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "x",
        "x",
    ]

    assert use_names(result) == [
        "x",
        "x",
        "x",
    ]


# Augmented assignment


def test_augmented_assignment_is_use_and_definition():
    source = """
def test():
    x = 10
    x += 5
    return x
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "x",
        "x",
    ]

    assert use_names(result) == [
        "x",
        "x",
    ]


# Unpacking


def test_tuple_unpacking_creates_multiple_definitions():
    source = """
def test():
    a, b = get_values()
    return a + b
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "a",
        "b",
    ]

    assert use_names(result) == [
        "get_values",
        "a",
        "b",
    ]


# Function calls


def test_function_call_arguments_are_uses():
    source = """
def test(x):
    y = calculate(x)
    return y
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "x",
        "y",
    ]

    assert use_names(result) == [
        "calculate",
        "x",
        "y",
    ]


# Nested functions


def test_nested_function_is_not_analyzed_as_outer_function():
    source = """
def test(x):
    y = x + 1

    def inner(z):
        a = z + 10
        return a

    return y
"""

    result = analyze_function(source)

    assert definition_names(result) == [
        "x",
        "y",
    ]

    assert use_names(result) == [
        "x",
        "y",
    ]


# Properties


def test_defined_variables_property():
    source = """
def test():
    x = 10
    y = 20
    return x
"""

    result = analyze_function(source)

    assert result.defined_variables == {"x", "y"}


def test_used_variables_property():
    source = """
def test(x):
    y = x + 10
    return y
"""

    result = analyze_function(source)

    assert result.used_variables == {"x", "y"}