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
    sanitizer_names=None,
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
        sanitizer_names=sanitizer_names,
    )

    return (
        data_flow,
        reaching,
        def_use,
        result,
    )


# ================================================================
# V1 - SOURCE / SINK TESTS
# ================================================================


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


# ================================================================
# V2 - PROPAGATION TESTS
# ================================================================


def test_taint_propagates_through_variable_assignment():
    source = """
def test():
    user_input = request_input()
    query = user_input
    execute(query)
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
    assert finding.variable == "query"

    assert finding.path == (
        "request_input",
        "query",
        "execute",
    )


def test_taint_propagates_through_multiple_assignments():
    source = """
def test():
    user_input = request_input()
    query = user_input
    final_query = query
    execute(final_query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "final_query"

    assert finding.path == (
        "request_input",
        "final_query",
        "execute",
    )


def test_taint_propagates_through_string_concatenation():
    source = """
def test():
    user_input = request_input()
    query = "SELECT * FROM users WHERE id=" + user_input
    execute(query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "query"


def test_taint_propagates_through_f_string():
    source = """
def test():
    user_input = request_input()
    query = f"SELECT * FROM users WHERE id={user_input}"
    execute(query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "query"


def test_taint_does_not_propagate_from_constant_assignment():
    source = """
def test():
    user_input = request_input()
    query = user_input
    query = "safe"
    execute(query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_taint_propagates_through_expression_with_multiple_variables():
    source = """
def test():
    first = request_input()
    second = "constant"
    query = first + second
    execute(query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "query"


def test_clean_expression_is_not_tainted():
    source = """
def test():
    first = 10
    second = 20
    query = first + second
    execute(query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_direct_source_inside_sink_is_reported():
    source = """
def test():
    execute(request_input())
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


def test_taint_propagates_through_method_call_result():
    source = """
def test():
    user_input = request_input()
    query = user_input.strip()
    execute(query)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1

    finding = result.findings[0]

    assert finding.variable == "query"


def test_multiple_tainted_variables_reach_different_sinks():
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

    variables = {
        finding.variable
        for finding in result.findings
    }

    assert variables == {
        "first",
        "second",
    }


# ================================================================
# V3 - SANITIZER TESTS
# ================================================================


def test_sanitizer_blocks_taint():
    source = """
def test():
    user_input = request_input()
    safe = sanitize(user_input)
    execute(safe)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sanitizer_names={"sanitize"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_unsanitized_value_still_reaches_sink():
    source = """
def test():
    user_input = request_input()
    execute(user_input)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sanitizer_names={"sanitize"},
        sink_names={"execute"},
    )

    assert result.finding_count == 1


def test_sanitizer_is_recorded():
    source = """
def test():
    user_input = request_input()
    safe = sanitize(user_input)
    execute(safe)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sanitizer_names={"sanitize"},
        sink_names={"execute"},
    )

    assert len(result.sanitizers) == 1
    assert result.sanitizers[0].name == "sanitize"


def test_custom_sanitizer_blocks_taint():
    source = """
def test():
    user_input = request_input()
    safe = clean_input(user_input)
    execute(safe)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sanitizer_names={"clean_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


# ================================================================
# V4 - VULNERABILITY RULE TESTS
# ================================================================


def test_sql_injection_is_classified():
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

    assert result.vulnerability_count == 1

    vulnerability = result.vulnerabilities[0]

    assert vulnerability.rule_id == "SQL_INJECTION"
    assert vulnerability.name == "SQL Injection"
    assert vulnerability.severity == "CRITICAL"


def test_command_injection_is_classified():
    source = """
def test():
    user_input = request_input()
    run_command(user_input)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"run_command"},
    )

    assert result.vulnerability_count == 1

    vulnerability = result.vulnerabilities[0]

    assert vulnerability.rule_id == "COMMAND_INJECTION"
    assert vulnerability.severity == "CRITICAL"


def test_path_traversal_is_classified():
    source = """
def test():
    user_input = request_input()
    open_file(user_input)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"open_file"},
    )

    assert result.vulnerability_count == 1

    vulnerability = result.vulnerabilities[0]

    assert vulnerability.rule_id == "PATH_TRAVERSAL"
    assert vulnerability.severity == "HIGH"


def test_no_matching_vulnerability_rule():
    source = """
def test():
    user_input = request_input()
    print(user_input)
"""

    _, _, _, result = analyze_function(
        source,
        source_names={"request_input"},
        sink_names={"print"},
    )

    assert result.finding_count == 1
    assert result.vulnerability_count == 0


# ================================================================
# V5 - INTERPROCEDURAL TESTS
# ================================================================


def test_interprocedural_source_to_sink():
    source = """
def get_data():
    return request_input()


def execute_data(value):
    execute(value)


def main():
    data = get_data()
    execute_data(data)
"""

    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    result = TaintAnalyzer().analyze_project(
        functions=functions,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count >= 1


def test_interprocedural_parameter_propagation():
    source = """
def execute_data(value):
    execute(value)


def main():
    user_input = request_input()
    execute_data(user_input)
"""

    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    result = TaintAnalyzer().analyze_project(
        functions=functions,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count >= 1


def test_interprocedural_sanitizer_blocks_flow():
    source = """
def execute_data(value):
    safe = sanitize(value)
    execute(safe)


def main():
    user_input = request_input()
    execute_data(user_input)
"""

    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    result = TaintAnalyzer().analyze_project(
        functions=functions,
        source_names={"request_input"},
        sanitizer_names={"sanitize"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_interprocedural_clean_value_is_not_reported():
    source = """
def execute_data(value):
    execute(value)


def main():
    value = 100
    execute_data(value)
"""

    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    result = TaintAnalyzer().analyze_project(
        functions=functions,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.finding_count == 0


def test_project_result_contains_vulnerability():
    source = """
def execute_data(value):
    execute(value)


def main():
    user_input = request_input()
    execute_data(user_input)
"""

    tree = ast.parse(source)

    functions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    result = TaintAnalyzer().analyze_project(
        functions=functions,
        source_names={"request_input"},
        sink_names={"execute"},
    )

    assert result.vulnerability_count >= 1

    vulnerability = result.vulnerabilities[0]

    assert vulnerability.rule_id == "SQL_INJECTION"
    assert vulnerability.severity == "CRITICAL"