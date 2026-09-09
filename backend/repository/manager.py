from __future__ import annotations

from pathlib import Path

from backend.core.config import settings


class RepositoryManager:
    """Validate and enumerate repositories allowed for analysis."""

    def __init__(self, repository_path: str | Path):
        self.repository_path = self._resolve_safe_path(repository_path)

    def _resolve_safe_path(self, repository_path: str | Path) -> Path:
        if repository_path is None or not str(repository_path).strip():
            raise ValueError("Repository path cannot be empty")

        allowed_root = settings.ALLOWED_ANALYSIS_ROOT.resolve()
        raw_path = Path(str(repository_path)).expanduser()
        candidate = raw_path.resolve() if raw_path.is_absolute() else (allowed_root / raw_path).resolve()

        try:
            candidate.relative_to(allowed_root)
        except ValueError as exc:
            raise ValueError(
                "Repository path is outside the allowed analysis directory: "
                f"{repository_path}"
            ) from exc

        return candidate

    def validate_repository(self) -> bool:
        return self.repository_path.is_dir()

    def get_python_files(self) -> list[Path]:
        if not self.validate_repository():
            raise ValueError(f"Invalid repository path: {self.repository_path}")

        files: list[Path] = []
        for path in self.repository_path.rglob("*.py"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            files.append(path)

        return sorted(files)
