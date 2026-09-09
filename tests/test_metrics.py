import ast

from backend.analysis.metrics import MetricsAnalyzer


def analyze(source: str):
    tree = ast.parse(source)

    analyzer = MetricsAnalyzer()
    analyzer.visit(tree)

    return analyzer.metrics


def test_metrics_analyzer_simple_function():
    source = """
def add(a, b):
    return a + b
"""

    metrics = analyze(source)

    assert len(metrics) == 1

    metric = metrics[0]

    assert metric.name == "add"
    assert metric.parameters == 2
    assert metric.branches == 0
    assert metric.loops == 0
    assert metric.function_calls == 0
    assert metric.cyclomatic_complexity == 1


def test_metrics_analyzer_counts_branches_and_loops():
    source = """
def process(items):
    if items:
        for item in items:
            print(item)
    return items
"""

    metrics = analyze(source)

    metric = metrics[0]

    assert metric.branches == 1
    assert metric.loops == 1
    assert metric.function_calls == 1
    assert metric.cyclomatic_complexity == 3
    assert metric.nesting_depth == 2


def test_metrics_analyzer_counts_boolean_decisions():
    source = """
def check(a, b, c):
    if a and b and c:
        return True
    return False
"""

    metrics = analyze(source)

    metric = metrics[0]

    assert metric.branches == 1
    assert metric.cyclomatic_complexity == 4


def test_metrics_analyzer_ignores_nested_function_metrics():
    source = """
def outer():
    if True:
        print("outer")

    def inner():
        for item in items:
            print(item)

    return inner
"""

    metrics = analyze(source)

    assert len(metrics) == 2

    outer = metrics[0]
    inner = metrics[1]

    assert outer.name == "outer"
    assert outer.branches == 1
    assert outer.loops == 0

    assert inner.name == "inner"
    assert inner.loops == 1


def test_metrics_analyzer_counts_async_functions():
    source = """
async def fetch(url):
    response = await request(url)
    return response
"""

    metrics = analyze(source)

    assert len(metrics) == 1
    assert metrics[0].name == "fetch"
    assert metrics[0].parameters == 1