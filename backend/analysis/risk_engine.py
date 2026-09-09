from __future__ import annotations

import os
from pathlib import Path


class RiskEngine:
    """Score function and file risk using deterministic structural signals."""

    def __init__(self, graph_analyzer=None, repository_path=None):
        self.graph_analyzer = graph_analyzer
        self.repository_path = (
            Path(repository_path).resolve() if repository_path else None
        )

    def calculate_function_risk(self, metrics):
        score = 0
        reasons: list[str] = []

        complexity = metrics.cyclomatic_complexity
        if complexity >= 10:
            score += 30
            reasons.append("Very high cyclomatic complexity")
        elif complexity >= 7:
            score += 20
            reasons.append("High cyclomatic complexity")
        elif complexity >= 4:
            score += 10
            reasons.append("Moderate cyclomatic complexity")

        lines = metrics.lines_of_code
        if lines >= 100:
            score += 20
            reasons.append("Very large function")
        elif lines >= 50:
            score += 10
            reasons.append("Large function")
        elif lines >= 30:
            score += 5
            reasons.append("Long function")

        parameters = metrics.parameters
        if parameters >= 7:
            score += 15
            reasons.append("Too many parameters")
        elif parameters >= 5:
            score += 8
            reasons.append("Many parameters")
        elif parameters >= 3:
            score += 3
            reasons.append("Several parameters")

        nesting = metrics.nesting_depth
        if nesting >= 5:
            score += 20
            reasons.append("Very deep nesting")
        elif nesting >= 3:
            score += 10
            reasons.append("Deep nesting")
        elif nesting >= 2:
            score += 5
            reasons.append("Nested control flow")

        branches = metrics.branches
        if branches >= 8:
            score += 15
            reasons.append("Many branches")
        elif branches >= 4:
            score += 8
            reasons.append("Several branches")
        elif branches >= 2:
            score += 3
            reasons.append("Multiple branches")

        loops = metrics.loops
        if loops >= 4:
            score += 10
            reasons.append("Many loops")
        elif loops >= 2:
            score += 5
            reasons.append("Multiple loops")
        elif loops >= 1:
            score += 2
            reasons.append("Contains loop")

        calls = metrics.function_calls
        if calls >= 15:
            score += 10
            reasons.append("Many function calls")
        elif calls >= 8:
            score += 5
            reasons.append("Several function calls")

        score = min(int(score), 100)
        return {
            "name": metrics.name,
            "line": metrics.line,
            "score": score,
            "level": self._get_risk_level(score),
            "reasons": reasons,
        }

    @staticmethod
    def _get_risk_level(score: int) -> str:
        if score >= 70:
            return "CRITICAL"
        if score >= 40:
            return "HIGH"
        if score >= 20:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _get_file_path(analysis_result):
        if hasattr(analysis_result, "file_path"):
            return str(analysis_result.file_path)
        if hasattr(analysis_result, "path"):
            return str(analysis_result.path)
        return None

    def _normalize_file_path(self, file_path):
        if not file_path:
            return None

        path = Path(file_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()

        if self.repository_path:
            try:
                return path.relative_to(self.repository_path).as_posix()
            except ValueError:
                return os.path.relpath(path, self.repository_path)

        return str(path)

    def calculate_file_risk(self, analysis_result):
        metrics = getattr(analysis_result, "metrics", [])
        file_path = self._get_file_path(analysis_result)
        graph_file_path = self._normalize_file_path(file_path)

        function_risks = [
            self.calculate_function_risk(function_metrics)
            for function_metrics in metrics
        ]

        if function_risks:
            scores = [risk["score"] for risk in function_risks]
            highest_score = max(scores)
            average_score = sum(scores) / len(scores)
            file_score = round(highest_score * 0.7 + average_score * 0.3)
        else:
            highest_score = 0
            file_score = 0

        reasons: list[str] = []
        if highest_score >= 70:
            reasons.append("Contains a highly risky function")
        elif highest_score >= 40:
            reasons.append("Contains a high-risk function")
        elif highest_score >= 20:
            reasons.append("Contains a moderately risky function")

        if self.graph_analyzer and graph_file_path:
            dependent_count = self.graph_analyzer.get_dependent_count(graph_file_path)
            if dependent_count >= 5:
                file_score += 20
                reasons.append("Many files depend on this file")
            elif dependent_count >= 3:
                file_score += 12
                reasons.append("Several files depend on this file")
            elif dependent_count >= 1:
                file_score += 5
                reasons.append("Other files depend on this file")

            if any(
                graph_file_path in cycle
                for cycle in self.graph_analyzer.find_circular_dependencies()
            ):
                file_score += 20
                reasons.append("File is part of a circular dependency")

        if len(metrics) >= 10:
            file_score += 5
            reasons.append("File contains many functions")

        file_score = min(round(file_score), 100)
        return {
            "file": file_path,
            "score": file_score,
            "level": self._get_risk_level(file_score),
            "functions": function_risks,
            "reasons": reasons,
        }

    def analyze_project(self, analysis_results):
        return [
            self.calculate_file_risk(analysis_result)
            for analysis_result in analysis_results
        ]
