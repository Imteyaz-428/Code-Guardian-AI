from backend.analysis.project_analyzer import ProjectAnalyzer


def test_project_analyzer_analyzes_sample_project():
    repository_path = "tests/sample_project"

    analyzer = ProjectAnalyzer(repository_path)

    results = analyzer.analyze()

    assert isinstance(results, list)
    assert len(results) == 3
    assert all(result.file_path for result in results)
    assert any(result.functions for result in results)
    assert any(result.metrics for result in results)


def test_project_analyzer_continues_after_invalid_python(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.repository.manager.settings.ALLOWED_ANALYSIS_ROOT",
        tmp_path,
    )

    good_file = tmp_path / "good.py"
    broken_file = tmp_path / "broken.py"

    good_file.write_text(
        "def hello():\n    return 'hello'\n",
        encoding="utf-8",
    )

    broken_file.write_text(
        "def broken(:\n    pass\n",
        encoding="utf-8",
    )

    analyzer = ProjectAnalyzer(tmp_path)

    results = analyzer.analyze()

    assert len(results) == 1
    assert results[0].file_path == str(good_file)

    assert len(analyzer.errors) == 1
    assert "Syntax error" in analyzer.errors[0]