from __future__ import annotations

from pathlib import Path

from backend.analysis.call_graph import CallGraphAnalyzer
from backend.analysis.cfg import CFGAnalyzer
from backend.analysis.function_collector import FunctionCollector
from backend.analysis.metrics import MetricsAnalyzer
from backend.models.analysis_result import AnalysisResult
from backend.parsing.ast_parser import ASTParser, CodeExtractor
from backend.repository.manager import RepositoryManager


class ProjectAnalyzer:
    """Analyze all supported source files in a repository."""

    def __init__(self, repository_path: str | Path):
        self.repository_manager = RepositoryManager(repository_path)

        self.errors: list[str] = []

        # Repository-level Call Graph.
        self.call_graph = None

        # Repository-level CFGs.
        #
        # function_id -> ControlFlowGraph
        self.control_flow_graphs = {}

    def analyze(self) -> list[AnalysisResult]:
        """Analyze the complete repository."""

        self.errors = []
        self.call_graph = None
        self.control_flow_graphs = {}

        results: list[AnalysisResult] = []
        trees = {}

        root = self.repository_manager.repository_path.resolve()

        for file_path in self.repository_manager.get_python_files():

            try:
                tree = ASTParser(file_path).parse()

            except ValueError as exc:
                self.errors.append(str(exc))
                continue

           
            # Convert file path to repository-relative path.
           

            relative_path = (
                file_path.resolve()
                .relative_to(root)
                .as_posix()
            )

            # Keep AST trees for repository-level analysis.
            trees[relative_path] = tree

           
            # AST extraction
           

            extractor = CodeExtractor()
            extractor.visit(tree)

            result = extractor.get_result(file_path)

           
            # Metrics analysis
           

            metrics_analyzer = MetricsAnalyzer()
            metrics_analyzer.visit(tree)

            result.metrics = metrics_analyzer.metrics

           
            # Function collection
           

            function_collector = FunctionCollector(relative_path)
            function_collector.visit(tree)

           
            # CFG analysis
           

            cfg_analyzer = CFGAnalyzer()

            for function_id, function_node in (
                function_collector.functions.items()
            ):
                cfg = cfg_analyzer.analyze(function_node)

                self.control_flow_graphs[function_id] = cfg

            results.append(result)

      
        # Repository-level Call Graph
      

        if trees:
            call_graph_analyzer = CallGraphAnalyzer()

            self.call_graph = call_graph_analyzer.analyze(
                trees
            )

        return results