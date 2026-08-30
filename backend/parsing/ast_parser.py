import ast
from pathlib import Path

from backend.models.analysis_result import (
    AnalysisResult,
    FunctionInfo,
    ClassInfo,
)


class ASTParser:

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def parse(self) -> ast.AST:
        """
        Read the Python file and convert it into an AST.
        """
        source_code = self.file_path.read_text(encoding="utf-8")

        return ast.parse(
            source_code,
            filename=str(self.file_path)
        )


class CodeExtractor(ast.NodeVisitor):

    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []

        self.function_calls = []
        self.conditions = 0
        self.loops = 0
        self.returns = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(
            FunctionInfo(
                name=node.name,
                line=node.lineno,
                parameters=[
                    arg.arg for arg in node.args.args
                ]
            )
        )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.functions.append(
            FunctionInfo(
                name=node.name,
                line=node.lineno,
                parameters=[
                    arg.arg for arg in node.args.args
                ]
            )
        )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(
            ClassInfo(
                name=node.name,
                line=node.lineno
            )
        )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)

        elif isinstance(node.func, ast.Attribute):
            self.function_calls.append(node.func.attr)

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self.conditions += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.loops += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.loops += 1
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        self.returns += 1
        self.generic_visit(node)

    def get_result(self, file_path: str | Path) -> AnalysisResult:
        """
        Convert the extracted information into an AnalysisResult.
        """
        return AnalysisResult(
            file_path=str(file_path),
            functions=self.functions,
            classes=self.classes,
            imports=self.imports,
            function_calls=self.function_calls,
            conditions=self.conditions,
            loops=self.loops,
            returns=self.returns,
        )