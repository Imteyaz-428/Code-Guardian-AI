from pathlib import Path

from backend.core.config import Settings


def test_settings_uses_project_root_by_default(monkeypatch):
    monkeypatch.delenv("CODE_GUARDIAN_ANALYSIS_ROOT", raising=False)

    settings = Settings()

    assert settings.ALLOWED_ANALYSIS_ROOT == settings.PROJECT_ROOT


def test_settings_uses_custom_analysis_root(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "CODE_GUARDIAN_ANALYSIS_ROOT",
        str(tmp_path),
    )

    settings = Settings()

    assert settings.ALLOWED_ANALYSIS_ROOT == tmp_path.resolve()


def test_settings_handles_empty_analysis_root(monkeypatch):
    monkeypatch.setenv("CODE_GUARDIAN_ANALYSIS_ROOT", "   ")

    settings = Settings()

    assert settings.ALLOWED_ANALYSIS_ROOT == settings.PROJECT_ROOT


def test_settings_parses_allowed_origins(monkeypatch):
    monkeypatch.setenv(
        "CODE_GUARDIAN_ALLOWED_ORIGINS",
        " http://localhost:5173, http://example.com ",
    )

    settings = Settings()

    assert settings.ALLOWED_ORIGINS == [
        "http://localhost:5173",
        "http://example.com",
    ]