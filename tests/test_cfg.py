import ast

from backend.analysis.cfg import CFGAnalyzer


def test_cfg_sequential_statements():
    source = """
def calculate():
    x = 10
    y = 20
    return x + y
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    assert graph.function_name == "calculate"

    assert len(graph.nodes) == 5

    assert graph.get_statistics() == {
        "function": "calculate",
        "nodes": 5,
        "edges": 4,
    }


def test_cfg_if_else():
    source = """
def check(x):
    if x > 0:
        return 1
    else:
        return -1
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    assert graph.function_name == "check"

    node_types = [node.type for node in graph.get_nodes()]

    assert "entry" in node_types
    assert "condition" in node_types
    assert "exit" in node_types

    assert len(graph.get_edges()) == 5


def test_cfg_for_loop():
    source = """
def process(items):
    for item in items:
        print(item)

    return True
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    assert graph.function_name == "process"

    node_types = [node.type for node in graph.get_nodes()]

    assert "entry" in node_types
    assert "loop" in node_types
    assert "exit" in node_types

    assert len(graph.get_edges()) >= 4
    
def test_cfg_while_loop():
    source = """
def process(items):
    while items:
        items.pop()

    return True
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    node_types = [node.type for node in graph.get_nodes()]

    assert "entry" in node_types
    assert "loop" in node_types
    assert "exit" in node_types

    loop_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "loop"
    ]

    assert len(loop_nodes) == 1

    loop_id = loop_nodes[0].id

    # The loop has two possible paths:
    # 1. Enter the loop body
    # 2. Exit the loop
    successors = graph.get_successors(loop_id)

    assert len(successors) == 2

    # Find the statement representing items.pop().
    body_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "statement"
        and node.line == 4
    ]

    assert len(body_nodes) == 1

    body_id = body_nodes[0].id

    # The loop must enter its body.
    assert body_id in successors

    # After executing the body, control returns
    # to the loop condition.
    assert loop_id in graph.get_successors(body_id)
def test_cfg_elif():
    source = """
def classify(x):
    if x > 10:
        return 1
    elif x > 0:
        return 2
    else:
        return 3
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    condition_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "condition"
    ]

    assert len(condition_nodes) == 2


def test_cfg_nested_if():
    source = """
def process(x):
    if x > 0:
        if x > 10:
            return 1
        return 2

    return 0
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    condition_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "condition"
    ]

    assert len(condition_nodes) == 2


def test_cfg_multiple_returns():
    source = """
def check(x):
    if x > 0:
        return 1

    if x == 0:
        return 0

    return -1
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    return_nodes = [
        node
        for node in graph.get_nodes()
        if node.label == "Return"
    ]

    assert len(return_nodes) == 3

    # Every return must connect directly to EXIT.
    exit_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "exit"
    ]

    assert len(exit_nodes) == 1

    exit_id = exit_nodes[0].id

    for return_node in return_nodes:
        assert exit_id in graph.get_successors(return_node.id)
        
        
def test_cfg_break():
    source = """
def process(items):
    while items:
        if items.empty():
            break

        work()
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    break_nodes = [
        node
        for node in graph.get_nodes()
        if node.label == "Break"
    ]

    assert len(break_nodes) == 1

    loop_exit_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "loop_exit"
    ]

    assert len(loop_exit_nodes) == 1

    assert loop_exit_nodes[0].id in graph.get_successors(
        break_nodes[0].id
    )


def test_cfg_continue():
    source = """
def process(items):
    while items:
        if items.empty():
            continue

        work()
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    continue_nodes = [
        node
        for node in graph.get_nodes()
        if node.label == "Continue"
    ]

    assert len(continue_nodes) == 1

    loop_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "loop"
    ]

    assert len(loop_nodes) == 1

    assert loop_nodes[0].id in graph.get_successors(
        continue_nodes[0].id
    )


def test_cfg_nested_loops():
    source = """
def process(items):
    while items:
        for item in items:
            if item < 0:
                break

        work()
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    loop_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "loop"
    ]

    assert len(loop_nodes) == 2

    break_nodes = [
        node
        for node in graph.get_nodes()
        if node.label == "Break"
    ]

    assert len(break_nodes) == 1

    # The break belongs to the INNER loop.
    inner_loop = max(
        loop_nodes,
        key=lambda node: node.id,
    )

    loop_exit_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "loop_exit"
    ]

    assert len(loop_exit_nodes) == 2

    inner_exit = max(
        loop_exit_nodes,
        key=lambda node: node.id,
    )

    assert inner_exit.id in graph.get_successors(
        break_nodes[0].id
    )


def test_cfg_try_except():
    source = """
def process():
    try:
        risky_operation()
    except ValueError:
        handle_error()
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    node_types = [
        node.type
        for node in graph.get_nodes()
    ]

    assert "try" in node_types
    assert "except" in node_types

    try_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "try"
    ]

    except_nodes = [
        node
        for node in graph.get_nodes()
        if node.type == "except"
    ]

    assert len(try_nodes) == 1
    assert len(except_nodes) == 1

    assert except_nodes[0].id in graph.get_successors(
        try_nodes[0].id
    )


def test_cfg_try_except_else_finally():
    source = """
def process():
    try:
        risky_operation()
    except ValueError:
        handle_error()
    else:
        success()
    finally:
        cleanup()
"""

    tree = ast.parse(source)
    function_node = tree.body[0]

    analyzer = CFGAnalyzer()
    graph = analyzer.analyze(function_node)

    node_types = [
        node.type
        for node in graph.get_nodes()
    ]

    assert "try" in node_types
    assert "except" in node_types
    assert "finally" in node_types