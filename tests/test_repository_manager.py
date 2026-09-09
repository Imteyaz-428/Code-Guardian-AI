import pytest
from backend.core.config import settings
from backend.repository.manager import RepositoryManager


def test_repository_manager_accepts_valid_repository(tmp_path, monkeypatch):
    allowed_root = tmp_path / "repositories"
    allowed_root.mkdir()

    monkeypatch.setattr(
        settings,
        "ALLOWED_ANALYSIS_ROOT",
        allowed_root,
    )

    repository = allowed_root / "sample_project"
    repository.mkdir()

    manager = RepositoryManager(repository)

    assert manager.validate_repository() is True
    assert manager.repository_path == repository.resolve()
    
    



def test_repository_manager_rejects_repository_outside_allowed_root(
    tmp_path,
    monkeypatch,
):
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()

    outside_root = tmp_path / "outside"
    outside_root.mkdir()

    monkeypatch.setattr(
        settings,
        "ALLOWED_ANALYSIS_ROOT",
        allowed_root,
    )

    with pytest.raises(ValueError, match="outside the allowed analysis directory"):
        RepositoryManager(outside_root)