from pathlib import Path

from backend.analysis.project_analyzer import ProjectAnalyzer
from backend.core import config


def test_project_analyzer_builds_call_graph(
    tmp_path: Path,
    monkeypatch,
):
    # Allow pytest's temporary directory for this test only.
    monkeypatch.setattr(
        config.settings,
        "ALLOWED_ANALYSIS_ROOT",
        tmp_path,
    )

    main_file = tmp_path / "main.py"

    main_file.write_text(
        """
def main():
    helper()

def helper():
    pass
"""
    )

    analyzer = ProjectAnalyzer(tmp_path)

    results = analyzer.analyze()

    assert len(results) == 1

    assert analyzer.call_graph is not None

    assert analyzer.call_graph.get_callees(
        "main.py::main"
    ) == [
        "main.py::helper",
    ]

    assert analyzer.call_graph.get_callers(
        "main.py::helper"
    ) == [
        "main.py::main",
    ]

    assert analyzer.call_graph.get_statistics() == {
        "functions": 2,
        "calls": 1,
    }
    
    
def test_project_analyzer_builds_cross_file_call_graph(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(
        config.settings,
        "ALLOWED_ANALYSIS_ROOT",
        tmp_path,
    )

    main_file = tmp_path / "main.py"
    auth_file = tmp_path / "auth.py"
    database_file = tmp_path / "database.py"

    main_file.write_text(
        """
from auth import login

def main():
    login()
"""
    )

    auth_file.write_text(
        """
from database import get_user

def login():
    get_user()
"""
    )

    database_file.write_text(
        """
def get_user():
    pass
"""
    )

    analyzer = ProjectAnalyzer(tmp_path)

    results = analyzer.analyze()

    assert len(results) == 3

    assert analyzer.call_graph is not None

    assert analyzer.call_graph.get_callees(
        "main.py::main"
    ) == [
        "auth.py::login",
    ]

    assert analyzer.call_graph.get_callees(
        "auth.py::login"
    ) == [
        "database.py::get_user",
    ]

    assert analyzer.call_graph.get_callers(
        "auth.py::login"
    ) == [
        "main.py::main",
    ]

    assert analyzer.call_graph.get_callers(
        "database.py::get_user"
    ) == [
        "auth.py::login",
    ]

    assert analyzer.call_graph.get_statistics() == {
        "functions": 3,
        "calls": 2,
    }