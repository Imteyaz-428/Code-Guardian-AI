from __future__ import annotations

from pathlib import Path

from backend.analysis.metrics import MetricsAnalyzer
from backend.models.analysis_result import AnalysisResult
from backend.parsing.ast_parser import ASTParser, CodeExtractor
from backend.repository.manager import RepositoryManager


class ProjectAnalyzer:
    """Analyze all supported source files in a repository."""

    def __init__(self, repository_path: str | Path):
        self.repository_manager = RepositoryManager(repository_path)
        self.errors: list[str] = []

    def analyze(self) -> list[AnalysisResult]:
        self.errors = []
        results: list[AnalysisResult] = []

        for file_path in self.repository_manager.get_python_files():
            try:
                tree = ASTParser(file_path).parse()
            except ValueError as exc:
                self.errors.append(str(exc))
                continue

            extractor = CodeExtractor()
            extractor.visit(tree)
            result = extractor.get_result(file_path)

            metrics_analyzer = MetricsAnalyzer()
            metrics_analyzer.visit(tree)
            result.metrics = metrics_analyzer.metrics
            results.append(result)

        return results
