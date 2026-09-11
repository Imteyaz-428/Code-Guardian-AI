from __future__ import annotations

import ast


class FunctionCollector(ast.NodeVisitor):
    """
    Collect functions and methods from an AST.

    Function IDs use the same format throughout
    Code Guardian AI.

    Examples:

        main.py::main

        services/user.py::UserService::get_user
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_stack.append(node.name)

        self.generic_visit(node)

        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        function_id = self._build_function_id(node.name)

        self.functions[function_id] = node

        self.generic_visit(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ):
        function_id = self._build_function_id(node.name)

        self.functions[function_id] = node

        self.generic_visit(node)

    def _build_function_id(self, function_name: str) -> str:
        """
        Build a unique function identifier.
        """

        if self.class_stack:
            class_name = "::".join(self.class_stack)

            return (
                f"{self.file_path}::"
                f"{class_name}::"
                f"{function_name}"
            )

        return f"{self.file_path}::{function_name}"