import ast

from backend.models.analysis_result import FunctionMetrics


class MetricsAnalyzer(ast.NodeVisitor):

    def __init__(self):
        self.metrics = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        metrics = self._analyze_function(node)

        self.metrics.append(metrics)

        # Don't analyze nested functions as part of the parent.
        # They will be analyzed separately.
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        metrics = self._analyze_function(node)

        self.metrics.append(metrics)

        return

    def _analyze_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> FunctionMetrics:

        lines_of_code = (
            node.end_lineno - node.lineno + 1
        )

        parameters = len(node.args.args)

        branches = 0
        loops = 0
        function_calls = 0

        max_nesting_depth = 0

        for child in ast.walk(node):

            if isinstance(child, ast.If):
                branches += 1

            elif isinstance(child, (ast.For, ast.While)):
                loops += 1

            elif isinstance(child, ast.Call):
                function_calls += 1

        # Calculate maximum nesting depth
        def calculate_depth(node, current_depth=0):

            nonlocal max_nesting_depth

            nesting_nodes = (
                ast.If,
                ast.For,
                ast.While,
                ast.Try,
                ast.With
            )

            if isinstance(node, nesting_nodes):
                current_depth += 1

                max_nesting_depth = max(
                    max_nesting_depth,
                    current_depth
                )

            for child in ast.iter_child_nodes(node):
                calculate_depth(child, current_depth)

        calculate_depth(node)

        # Cyclomatic complexity
        decision_points = 0

        for child in ast.walk(node):

            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.ExceptHandler,
                    ast.IfExp
                )
            ):
                decision_points += 1

            elif isinstance(child, ast.BoolOp):
                # Each additional boolean condition adds a path.
                decision_points += len(child.values) - 1

        cyclomatic_complexity = 1 + decision_points

        return FunctionMetrics(
            name=node.name,
            line=node.lineno,
            lines_of_code=lines_of_code,
            parameters=parameters,
            branches=branches,
            loops=loops,
            function_calls=function_calls,
            nesting_depth=max_nesting_depth,
            cyclomatic_complexity=cyclomatic_complexity,
        )