from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CodeCorrectionRequest:
    """Information required to generate a code correction."""

    file_path: str
    function_name: str
    source_code: str
    finding: str
    severity: str = "unknown"


@dataclass
class CodeCorrectionResult:
    """Proposed correction without modifying the original file."""

    file_path: str
    function_name: str
    original_code: str
    corrected_code: str | None
    explanation: str
    patch: str | None
    status: str


class CodeCorrectionService:
    """
    Prepare source code for correction and generate reviewable patches.

    This module does not call an AI provider yet.
    It never modifies the original source file.
    """

    def extract_function(
        self,
        file_path: str | Path,
        function_name: str,
    ) -> str:
        """
        Extract a function using its AST source location.
        Supports nested functions and async functions.
        """

        path = Path(file_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(
                f"Source file not found: {path}"
            )

        source = path.read_text(encoding="utf-8")
        lines = source.splitlines(keepends=True)

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise ValueError(
                f"Cannot parse source file: {exc}"
            ) from exc

        candidates = []

        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                if node.name == function_name:
                    candidates.append(node)

        if not candidates:
            raise ValueError(
                f"Function '{function_name}' was not found."
            )

        if len(candidates) > 1:
            raise ValueError(
                f"Multiple functions named '{function_name}' "
                "were found. A qualified function identifier "
                "is required to select the correct function."
            )

        function_node = candidates[0]

        # Include decorators when present.
        start_line = function_node.lineno

        if function_node.decorator_list:
            start_line = min(
                decorator.lineno
                for decorator in function_node.decorator_list
            )

        end_line = function_node.end_lineno

        if end_line is None:
            raise ValueError(
                "Could not determine the function's end line."
            )

        return "".join(lines[start_line - 1:end_line])

    def create_request(
        self,
        file_path: str | Path,
        function_name: str,
        finding: str,
        severity: str = "unknown",
    ) -> CodeCorrectionRequest:
        """Build the information an AI correction provider needs."""

        source_code = self.extract_function(
            file_path=file_path,
            function_name=function_name,
        )

        return CodeCorrectionRequest(
            file_path=str(Path(file_path).resolve()),
            function_name=function_name,
            source_code=source_code,
            finding=finding,
            severity=severity,
        )

    def generate_patch(
        self,
        original_code: str,
        corrected_code: str,
        file_path: str,
    ) -> str:
        """Generate a unified diff without changing any files."""

        original_lines = original_code.splitlines(
            keepends=True
        )
        corrected_lines = corrected_code.splitlines(
            keepends=True
        )

        return "".join(
            difflib.unified_diff(
                original_lines,
                corrected_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
            )
        )

    def create_result(
        self,
        request: CodeCorrectionRequest,
        corrected_code: str,
        explanation: str,
    ) -> CodeCorrectionResult:
        """
        Package a proposed correction.

        The caller must supply corrected code from a trusted
        correction workflow. This method does not generate code.
        """

        if not corrected_code.strip():
            raise ValueError(
                "Corrected code cannot be empty."
            )

        patch = self.generate_patch(
            original_code=request.source_code,
            corrected_code=corrected_code,
            file_path=request.file_path,
        )

        return CodeCorrectionResult(
            file_path=request.file_path,
            function_name=request.function_name,
            original_code=request.source_code,
            corrected_code=corrected_code,
            explanation=explanation,
            patch=patch,
            status="proposed",
        )