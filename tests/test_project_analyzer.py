from backend.analysis.project_analyzer import ProjectAnalyzer


repository_path = "tests/sample_project"

analyzer = ProjectAnalyzer(repository_path)

results = analyzer.analyze()

print(f"Files analyzed: {len(results)}")

for result in results:

    print("\n" + "=" * 50)
    print(f"FILE: {result.file_path}")

    print(f"Functions: {len(result.functions)}")

    for metric in result.metrics:
        print(
            f"  {metric.name} -> "
            f"LOC={metric.lines_of_code}, "
            f"Complexity={metric.cyclomatic_complexity}, "
            f"Nesting={metric.nesting_depth}"
        )