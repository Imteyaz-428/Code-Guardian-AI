from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """Central configuration for the Code Guardian backend."""

    PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

    def __init__(self) -> None:
        # Load environment variables from the project root .env file.
        load_dotenv(self.PROJECT_ROOT / ".env")

        # Repository analysis configuration
        self.ALLOWED_ANALYSIS_ROOT = self._get_analysis_root()
        self.ALLOWED_ORIGINS = self._get_allowed_origins()

        # API configuration
        self.API_TITLE = "Code Guardian AI"
        self.API_DESCRIPTION = (
            "Static code analysis and structural risk detection"
        )
        self.API_VERSION = "0.1.0"

        # Primary AI provider (backward compatibility)
        self.AI_PROVIDER = os.getenv(
            "CODE_GUARDIAN_AI_PROVIDER",
            "gemini",
        ).strip().lower()

        # AI provider fallback order
        configured_providers = os.getenv(
            "CODE_GUARDIAN_AI_PROVIDERS",
            "gemini,groq,deepseek",
        )

        self.AI_PROVIDERS = [
            provider.strip().lower()
            for provider in configured_providers.split(",")
            if provider.strip()
        ]

        # Remove duplicate provider names while preserving order.
        self.AI_PROVIDERS = list(dict.fromkeys(self.AI_PROVIDERS))

        # Gemini configuration
        self.GEMINI_API_KEY = os.getenv(
            "GEMINI_API_KEY",
            "",
        ).strip()

        self.GEMINI_MODEL = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        ).strip()

        # Groq configuration
        self.GROQ_API_KEY = os.getenv(
            "GROQ_API_KEY",
            "",
        ).strip()

        self.GROQ_MODEL = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        ).strip()

        # DeepSeek configuration
        self.DEEPSEEK_API_KEY = os.getenv(
            "DEEPSEEK_API_KEY",
            "",
        ).strip()

        self.DEEPSEEK_MODEL = os.getenv(
            "DEEPSEEK_MODEL",
            "deepseek-chat",
        ).strip()

    def _get_analysis_root(self) -> Path:
        """Return the root directory where repositories may be analyzed."""

        configured_root = os.getenv(
            "CODE_GUARDIAN_ANALYSIS_ROOT",
            "",
        ).strip()

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


# Initialize application settings
settings = Settings()