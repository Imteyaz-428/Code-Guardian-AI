from __future__ import annotations

import ast
from pathlib import Path

from backend.models.analysis_result import AnalysisResult, ClassInfo, FunctionInfo


class ASTParser:
    """Read a Python file and convert it into an abstract syntax tree."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def parse(self) -> ast.AST:
        try:
            source_code = self.file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Unable to decode {self.file_path} as UTF-8") from exc
        except OSError as exc:
            raise ValueError(f"Unable to read {self.file_path}: {exc}") from exc

        try:
            return ast.parse(source_code, filename=str(self.file_path))
        except SyntaxError as exc:
            location = f"line {exc.lineno}" if exc.lineno else "unknown line"
            raise ValueError(
                f"Syntax error in {self.file_path} at {location}: {exc.msg}"
            ) from exc


class CodeExtractor(ast.NodeVisitor):
    """Extract file-level structure and basic AST statistics."""

    def __init__(self):
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.imports: list[str] = []
        self.function_calls: list[str] = []
        self.conditions = 0
        self.loops = 0
        self.returns = 0

    @staticmethod
    def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        args = node.args
        names = [arg.arg for arg in args.posonlyargs]
        names.extend(arg.arg for arg in args.args)
        if args.vararg:
            names.append(f"*{args.vararg.arg}")
        names.extend(arg.arg for arg in args.kwonlyargs)
        if args.kwarg:
            names.append(f"**{args.kwarg.arg}")
        return names

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(
            FunctionInfo(
                name=node.name,
                line=node.lineno,
                parameters=self._parameter_names(node),
            )
        )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.functions.append(
            FunctionInfo(
                name=node.name,
                line=node.lineno,
                parameters=self._parameter_names(node),
            )
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(ClassInfo(name=node.name, line=node.lineno))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        self.imports.extend(alias.name for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = "." * node.level + (node.module or "")
        if module:
            self.imports.append(module)
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

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.loops += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.loops += 1
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        self.returns += 1
        self.generic_visit(node)

    def get_result(self, file_path: str | Path) -> AnalysisResult:
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
