from __future__ import annotations

import re
import shutil
import subprocess
import tempfile

from pathlib import Path
from urllib.parse import urlsplit

from backend.core.config import settings


def clone_github_repository(github_url: str) -> tuple[Path, Path]:
    """Clone a public GitHub repository inside the allowed analysis root."""

    parsed = urlsplit(github_url.strip())

    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Use a valid HTTPS GitHub repository URL, "
            "for example https://github.com/psf/requests."
        )

    parts = parsed.path.strip("/").split("/")

    if len(parts) != 2:
        raise ValueError(
            "The URL must have the format "
            "https://github.com/owner/repository."
        )

    owner, repo = parts

    if repo.endswith(".git"):
        repo = repo[:-4]

    valid_name = re.compile(r"^[A-Za-z0-9_.-]+$")

    if (
        not valid_name.fullmatch(owner)
        or not valid_name.fullmatch(repo)
        or owner in {".", ".."}
        or repo in {".", ".."}
    ):
        raise ValueError("Invalid GitHub repository owner or name.")

    clone_url = f"https://github.com/{owner}/{repo}.git"

    allowed_root = Path(settings.ALLOWED_ANALYSIS_ROOT).resolve()
    allowed_root.mkdir(parents=True, exist_ok=True)

    workspace = Path(
        tempfile.mkdtemp(
            prefix="code_guardian_github_",
            dir=str(allowed_root),
        )
    )

    repository_path = workspace / "repository"

    try:
        subprocess.run(
            [
                "git",
                "-c", "protocol.ext.allow=never",
                "-c", "protocol.file.allow=never",
                "clone",
                "--depth=1",
                "--no-recurse-submodules",
                "--",
                clone_url,
                str(repository_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        repository_path.resolve().relative_to(allowed_root)

        return repository_path, workspace

    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(workspace, ignore_errors=True)
        raise ValueError("GitHub clone timed out after 120 seconds.") from exc

    except subprocess.CalledProcessError as exc:
        shutil.rmtree(workspace, ignore_errors=True)
        raise ValueError(
            "Unable to clone the GitHub repository. "
            "Confirm that it exists and is public."
        ) from exc

    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise