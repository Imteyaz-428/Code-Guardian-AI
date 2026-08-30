from pathlib import Path

from backend.repository.manager import RepositoryManager
from backend.parsing.ast_parser import ASTParser, CodeExtractor
from backend.analysis.metrics import MetricsAnalyzer
from backend.models.analysis_result import AnalysisResult


class ProjectAnalyzer:

    def __init__(self, repository_path: str | Path):
        self.repository_manager = RepositoryManager(repository_path)

    def analyze(self) -> list[AnalysisResult]:
        """
        Analyze every Python file in the repository.
        """

        python_files = self.repository_manager.get_python_files()

        results = []

        for file_path in python_files:

            # Parse source code
            parser = ASTParser(file_path)
            tree = parser.parse()

            # Extract structural information
            extractor = CodeExtractor()
            extractor.visit(tree)

            result = extractor.get_result(file_path)

            # Calculate function metrics
            metrics_analyzer = MetricsAnalyzer()
            metrics_analyzer.visit(tree)

            result.metrics = metrics_analyzer.metrics

            results.append(result)

        return results