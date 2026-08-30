from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.risk.engine import RiskEngine


repository_path = "tests/sample_project"

analyzer = ProjectAnalyzer(repository_path)

results = analyzer.analyze()

risk_engine = RiskEngine()

print("\n========== CODE GUARDIAN RISK REPORT ==========\n")

for result in results:

    print(f"FILE: {result.file_path}")

    for metrics in result.metrics:

        finding = risk_engine.calculate_risk(metrics)

        print(
            f"\n{finding.function_name}()"
        )

        print(
            f"Risk Score: {finding.score}/100"
        )

        print(
            f"Risk Level: {finding.level}"
        )

        if finding.reasons:

            print("Reasons:")

            for reason in finding.reasons:
                print(f"  - {reason}")

        else:
            print("Reasons: No major structural concerns")

    print()