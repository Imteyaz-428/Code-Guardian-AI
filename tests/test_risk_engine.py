from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.analysis.dependency_analyzer import DependencyAnalyzer
from backend.analysis.graph_analyzer import GraphAnalyzer
from backend.analysis.risk_engine import RiskEngine
from backend.models.analysis_result import FunctionMetrics


REPOSITORY_PATH = "tests/test_repo"


print("\nPROJECT ANALYSIS")

project_analyzer = ProjectAnalyzer(REPOSITORY_PATH)
analysis_results = project_analyzer.analyze()

print(f"Files analyzed: {len(analysis_results)}")


print("\nDEPENDENCY ANALYSIS")

dependency_analyzer = DependencyAnalyzer()
graph = dependency_analyzer.build_dependency_graph(REPOSITORY_PATH)

print("Graph created.")


graph_analyzer = GraphAnalyzer(graph)

print("\nGRAPH STATISTICS")
print(graph_analyzer.get_statistics())

print("\nADJACENCY LIST")

adjacency = graph_analyzer.build_adjacency_list()

for file, dependencies in adjacency.items():
    print(f"{file} -> {dependencies}")


risk_engine = RiskEngine(
    graph_analyzer=graph_analyzer,
    repository_path=REPOSITORY_PATH
)


print("\nFUNCTION RISKS")

for result in analysis_results:
    file_path = (
        result.file_path
        if hasattr(result, "file_path")
        else result.path
    )

    print(f"\nFile: {file_path}")

    for metrics in result.metrics:
        risk = risk_engine.calculate_function_risk(metrics)

        print(
            f"  {risk['name']} "
            f"(line {risk['line']}) -> "
            f"{risk['score']} [{risk['level']}]"
        )

        for reason in risk["reasons"]:
            print(f"      - {reason}")


print("\nFILE RISKS")

for result in analysis_results:
    risk = risk_engine.calculate_file_risk(result)

    print(f"\n{risk['file']}")
    print(f"  Score: {risk['score']}")
    print(f"  Level: {risk['level']}")

    if risk["reasons"]:
        print("  Reasons:")

        for reason in risk["reasons"]:
            print(f"    - {reason}")


print("\nPROJECT RISK")

project_risks = risk_engine.analyze_project(analysis_results)

for risk in project_risks:
    print(
        f"{risk['file']} -> "
        f"{risk['score']} [{risk['level']}]"
    )


print("\nDEPENDENCY IMPACT")

for file in adjacency:
    dependents = graph_analyzer.get_dependents(file)
    print(f"{file} <- {dependents}")


print("\nCIRCULAR DEPENDENCIES")

cycles = graph_analyzer.find_circular_dependencies()

if not cycles:
    print("No circular dependencies found.")
else:
    for cycle in cycles:
        print(" -> ".join(cycle))


print("\nRISK ENGINE UNIT TEST")

complex_metrics = FunctionMetrics(
    name="complex_function",
    line=10,
    lines_of_code=120,
    parameters=8,
    branches=10,
    loops=4,
    function_calls=20,
    nesting_depth=6,
    cyclomatic_complexity=12
)

complex_risk = risk_engine.calculate_function_risk(complex_metrics)

print(
    f"complex_function -> "
    f"{complex_risk['score']} "
    f"[{complex_risk['level']}]"
)

print("Reasons:")

for reason in complex_risk["reasons"]:
    print(f"  - {reason}")


assert complex_risk["score"] > 70
assert complex_risk["level"] == "CRITICAL"
assert len(complex_risk["reasons"]) > 0

print("\nALL RISK TESTS PASSED")