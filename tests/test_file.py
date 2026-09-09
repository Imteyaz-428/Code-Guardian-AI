from backend.analysis.dependency_analyzer import DependencyAnalyzer
from backend.analysis.graph_analyzer import GraphAnalyzer


analyzer = DependencyAnalyzer()

# Build graph for the entire repository
graph = analyzer.build_dependency_graph(
    "tests/test_repo"
)

graph_analyzer = GraphAnalyzer(graph)


print("\n=== GRAPH STATISTICS ===")

print(
    graph_analyzer.get_statistics()
)


print("\n=== ADJACENCY LIST ===")

adjacency = graph_analyzer.build_adjacency_list()

for file, dependencies in adjacency.items():

    print(f"{file} -> {dependencies}")


print("\n=== DEPENDENCIES ===")

for dependency in graph_analyzer.get_dependencies("main.py"):

    print(f"main.py -> {dependency}")


print("\n=== DEPENDENTS ===")

for dependent in graph_analyzer.get_dependents("utils.py"):

    print(f"{dependent} -> utils.py")


print("\n=== CIRCULAR DEPENDENCIES ===")

cycles = graph_analyzer.find_circular_dependencies()

if not cycles:

    print("No circular dependencies found.")

else:

    for cycle in cycles:

        print(" -> ".join(cycle))