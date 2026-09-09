from __future__ import annotations

import ast
from pathlib import Path

from backend.analysis.language_detector import LanguageDetector
from backend.analysis.dependency_graph import DependencyGraph


class DependencyAnalyzer:
    """Build a local Python import/dependency graph."""

    def __init__(self):
        self.language_detector = LanguageDetector()

    @staticmethod
    def _read_source(file_path: str | Path) -> str:
        path = Path(file_path)
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Unable to decode {path} as UTF-8") from exc
        except OSError as exc:
            raise ValueError(f"Unable to read {path}: {exc}") from exc

    def parse_python_file(self, file_path: str | Path) -> ast.AST:
        source_code = self._read_source(file_path)
        try:
            return ast.parse(source_code, filename=str(file_path))
        except SyntaxError as exc:
            location = f"line {exc.lineno}" if exc.lineno else "unknown line"
            raise ValueError(
                f"Syntax error in {file_path} at {location}: {exc.msg}"
            ) from exc

    def analyze_file(self, file_path: str | Path) -> list[str]:
        """Return import module names found in a Python file."""
        if self.language_detector.detect_from_file(file_path) != "python":
            return []

        tree = self.parse_python_file(file_path)
        dependencies: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                dependencies.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                if module:
                    dependencies.append(module)

        return dependencies

    def get_file_metadata(self, file_path: str | Path) -> dict:
        """Extract language and structural metadata from a supported file."""
        path = Path(file_path)
        language = self.language_detector.detect_from_file(path)
        source_code = self._read_source(path)
        lines = len(source_code.splitlines())

        metadata = {
            "language": language,
            "lines": lines,
            "functions": 0,
            "methods": 0,
            "classes": 0,
            "imports": 0,
            "functions_detail": [],
            "methods_detail": [],
            "classes_detail": [],
        }

        if language != "python":
            return metadata

        tree = self.parse_python_file(path)

        class_stack: list[str] = []

        class MetadataVisitor(ast.NodeVisitor):
            def visit_ClassDef(inner_self, node: ast.ClassDef):
                metadata["classes"] += 1
                metadata["classes_detail"].append(
                    {"name": node.name, "line": node.lineno}
                )
                class_stack.append(node.name)
                inner_self.generic_visit(node)
                class_stack.pop()

            def visit_FunctionDef(inner_self, node: ast.FunctionDef):
                target = metadata["methods_detail"] if class_stack else metadata["functions_detail"]
                target.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        **({"class": class_stack[-1]} if class_stack else {}),
                    }
                )
                key = "methods" if class_stack else "functions"
                metadata[key] += 1
                inner_self.generic_visit(node)

            def visit_AsyncFunctionDef(inner_self, node: ast.AsyncFunctionDef):
                target = metadata["methods_detail"] if class_stack else metadata["functions_detail"]
                target.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        **({"class": class_stack[-1]} if class_stack else {}),
                    }
                )
                key = "methods" if class_stack else "functions"
                metadata[key] += 1
                inner_self.generic_visit(node)

            def visit_Import(inner_self, node: ast.Import):
                metadata["imports"] += 1

            def visit_ImportFrom(inner_self, node: ast.ImportFrom):
                metadata["imports"] += 1

        MetadataVisitor().visit(tree)
        return metadata

    @staticmethod
    def _resolve_module_path(
        module: str,
        repository_path: Path,
        current_file: Path | None = None,
        level: int = 0,
    ) -> Path | None:
        """Resolve an import to a local .py file when possible."""
        base = repository_path

        if level:
            if current_file is None:
                return None
            base = current_file.parent
            for _ in range(max(level - 1, 0)):
                base = base.parent

        parts = [part for part in module.split(".") if part]
        candidate_base = base.joinpath(*parts)

        # module.py
        module_file = candidate_base.with_suffix(".py")
        if module_file.is_file():
            return module_file

        # package/__init__.py
        package_init = candidate_base / "__init__.py"
        if package_init.is_file():
            return package_init

        return None

    def resolve_dependency(
        self,
        dependency: str,
        repository_path: str | Path,
        current_file: str | Path | None = None,
    ) -> str | None:
        """Resolve a local dependency and return its repository-relative path."""
        repository = Path(repository_path).resolve()
        current = Path(current_file).resolve() if current_file else None

        level = len(dependency) - len(dependency.lstrip("."))
        module = dependency[level:]
        resolved = self._resolve_module_path(
            module,
            repository,
            current,
            level,
        )

        if resolved is None:
            return None

        try:
            return resolved.relative_to(repository).as_posix()
        except ValueError:
            return None

    def build_dependency_graph(self, repository_path: str | Path) -> dict:
        """Analyze all Python files and build a dependency graph."""
        repository = Path(repository_path).resolve()

        if not repository.is_dir():
            raise ValueError(f"Invalid repository path: {repository}")

        graph = DependencyGraph()

        python_files = sorted(
            path
            for path in repository.rglob("*.py")
            if path.is_file()
            and "__pycache__" not in path.parts
        )

        # Add every Python file as a graph node.
        for file_path in python_files:
            relative_file = file_path.relative_to(repository).as_posix()

            try:
                metadata = self.get_file_metadata(file_path)
            except ValueError:
                # Keep the file visible even if it has invalid
                # syntax or encoding.
                metadata = {
                    "language": "python",
                    "lines": 0,
                    "functions": 0,
                    "methods": 0,
                    "classes": 0,
                    "imports": 0,
                    "functions_detail": [],
                    "methods_detail": [],
                    "classes_detail": [],
                }

            graph.add_file_node(relative_file, metadata)

        # Add dependency edges.
        for file_path in python_files:
            relative_file = file_path.relative_to(repository).as_posix()

            try:
                tree = self.parse_python_file(file_path)
            except ValueError:
                # One invalid file should not stop the whole project analysis.
                continue

            imports: list[tuple[str, int]] = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(
                        (alias.name, 0)
                        for alias in node.names
                    )

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imports.append((module, node.level))

            for module, level in imports:
                dependency = "." * level + module

                resolved_file = self.resolve_dependency(
                    dependency,
                    repository,
                    file_path,
                )

                if resolved_file is not None:
                    graph.add_edge(
                        relative_file,
                        resolved_file,
                        "import",
                    )

        return graph.to_dict()