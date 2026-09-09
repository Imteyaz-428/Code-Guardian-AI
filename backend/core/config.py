from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Central configuration for the Code Guardian backend."""

    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

    def __init__(self) -> None:
        self.ALLOWED_ANALYSIS_ROOT = self._get_analysis_root()
        self.ALLOWED_ORIGINS = self._get_allowed_origins()

        self.API_TITLE = "Code Guardian AI"
        self.API_DESCRIPTION = (
            "Static code analysis and structural risk detection"
        )
        self.API_VERSION = "0.1.0"

    def _get_analysis_root(self) -> Path:
        """Return the root directory where repositories may be analyzed."""

        configured_root = os.getenv("CODE_GUARDIAN_ANALYSIS_ROOT", "").strip()

        if not configured_root:
            configured_root = str(self.PROJECT_ROOT)

        return Path(configured_root).expanduser().resolve()

    def _get_allowed_origins(self) -> list[str]:
        """Return configured CORS origins."""

        configured_origins = os.getenv(
            "CODE_GUARDIAN_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )

        return [
            origin.strip()
            for origin in configured_origins.split(",")
            if origin.strip()
        ]


settings = Settings()