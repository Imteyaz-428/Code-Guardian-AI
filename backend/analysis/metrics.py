from __future__ import annotations

import ast

from backend.models.analysis_result import FunctionMetrics


class _FunctionBodyVisitor(ast.NodeVisitor):
    """Collect metrics for one function without entering nested functions."""

    NESTING_TYPES = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
        ast.Match,
    )

    def __init__(self):
        self.branches = 0
        self.loops = 0
        self.function_calls = 0
        self.decision_points = 0
        self.max_nesting_depth = 0

    def collect(self, function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        def walk(node: ast.AST, depth: int = 0) -> None:
            # A nested function/lambda has its own metrics and should not
            # inflate the metrics of the enclosing function.
            if node is not function_node and isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
            ):
                return

            current_depth = depth
            if node is not function_node and isinstance(node, self.NESTING_TYPES):
                current_depth += 1
                self.max_nesting_depth = max(
                    self.max_nesting_depth, current_depth
                )

            if isinstance(node, ast.If):
                self.branches += 1
                self.decision_points += 1
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                self.loops += 1
                self.decision_points += 1
            elif isinstance(node, ast.ExceptHandler):
                self.decision_points += 1
            elif isinstance(node, ast.IfExp):
                self.decision_points += 1
            elif isinstance(node, ast.BoolOp):
                self.decision_points += max(0, len(node.values) - 1)
            elif isinstance(node, ast.Match):
                case_count = sum(
                    1
                    for case in node.cases
                    if not (
                        isinstance(case.pattern, ast.MatchAs)
                        and case.pattern.name is None
                    )
                )
                self.decision_points += case_count
            elif isinstance(node, ast.Call):
                self.function_calls += 1

            for child in ast.iter_child_nodes(node):
                walk(child, current_depth)

        walk(function_node)


class MetricsAnalyzer(ast.NodeVisitor):
    """Calculate structural metrics for every function/method in a file."""

    def __init__(self):
        self.metrics: list[FunctionMetrics] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.metrics.append(self._analyze_function(node))
        # Nested functions are discovered separately by the outer AST walk.
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.metrics.append(self._analyze_function(node))
        self.generic_visit(node)

    @staticmethod
    def _parameter_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        args = node.args
        return (
            len(args.posonlyargs)
            + len(args.args)
            + len(args.kwonlyargs)
            + int(args.vararg is not None)
            + int(args.kwarg is not None)
        )

    def _analyze_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> FunctionMetrics:
        visitor = _FunctionBodyVisitor()
        visitor.collect(node)

        lines_of_code = (node.end_lineno or node.lineno) - node.lineno + 1
        complexity = 1 + visitor.decision_points

        return FunctionMetrics(
            name=node.name,
            line=node.lineno,
            lines_of_code=lines_of_code,
            parameters=self._parameter_count(node),
            branches=visitor.branches,
            loops=visitor.loops,
            function_calls=visitor.function_calls,
            nesting_depth=visitor.max_nesting_depth,
            cyclomatic_complexity=complexity,
        )
