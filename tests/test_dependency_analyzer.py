from pathlib import Path

import pytest

from backend.analysis.dependency_analyzer import DependencyAnalyzer


def test_dependency_analyzer_detects_imports(tmp_path: Path):
    source = """
import os
import json
from pathlib import Path
"""

    file_path = tmp_path / "sample.py"
    file_path.write_text(source, encoding="utf-8")

    analyzer = DependencyAnalyzer()

    dependencies = analyzer.analyze_file(file_path)

    assert "os" in dependencies
    assert "json" in dependencies
    assert "pathlib" in dependencies


def test_dependency_analyzer_returns_empty_for_non_python(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello", encoding="utf-8")

    analyzer = DependencyAnalyzer()

    dependencies = analyzer.analyze_file(file_path)

    assert dependencies == []


def test_dependency_analyzer_extracts_metadata(tmp_path: Path):
    source = """
import os


class Example:
    def method(self):
        return os.getcwd()


def helper():
    return 42
"""

    file_path = tmp_path / "sample.py"
    file_path.write_text(source, encoding="utf-8")

    analyzer = DependencyAnalyzer()

    metadata = analyzer.get_file_metadata(file_path)

    assert metadata["language"] == "python"
    assert metadata["lines"] == len(source.splitlines())
    assert metadata["classes"] == 1
    assert metadata["methods"] == 1
    assert metadata["functions"] == 1
    assert metadata["imports"] == 1

    assert metadata["classes_detail"][0]["name"] == "Example"
    assert metadata["methods_detail"][0]["name"] == "method"
    assert metadata["functions_detail"][0]["name"] == "helper"


def test_dependency_analyzer_resolves_local_dependency(tmp_path: Path):
    repository = tmp_path / "repo"
    repository.mkdir()

    (repository / "main.py").write_text(
        "import utils\n",
        encoding="utf-8",
    )

    (repository / "utils.py").write_text(
        "def hello():\n    return 'hello'\n",
        encoding="utf-8",
    )

    analyzer = DependencyAnalyzer()

    resolved = analyzer.resolve_dependency(
        "utils",
        repository,
        repository / "main.py",
    )

    assert resolved == "utils.py"


def test_dependency_analyzer_builds_dependency_graph(tmp_path: Path):
    repository = tmp_path / "repo"
    repository.mkdir()

    (repository / "main.py").write_text(
        "import utils\n",
        encoding="utf-8",
    )

    (repository / "utils.py").write_text(
        "def hello():\n    return 'hello'\n",
        encoding="utf-8",
    )

    analyzer = DependencyAnalyzer()

    graph = analyzer.build_dependency_graph(repository)

    assert "nodes" in graph
    assert "edges" in graph

    node_files = [
        node["file"]
        for node in graph["nodes"]
    ]

    assert "main.py" in node_files
    assert "utils.py" in node_files

    assert any(
        edge["source"] == "main.py"
        and edge["target"] == "utils.py"
        for edge in graph["edges"]
    )


def test_dependency_analyzer_rejects_invalid_python(tmp_path: Path):
    file_path = tmp_path / "broken.py"

    file_path.write_text(
        "def broken(:\n",
        encoding="utf-8",
    )

    analyzer = DependencyAnalyzer()

    with pytest.raises(ValueError, match="Syntax error"):
        analyzer.analyze_file(file_path)