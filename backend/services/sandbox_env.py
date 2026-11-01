"""Builds (and caches) a Docker image that contains one repository's dependencies.

Put this file at: backend/services/sandbox_env.py

Flow: read the repo's dependency files -> add well-known imports that are not
declared -> `docker build` an image on top of the base sandbox image -> the
verifier then runs its checks (still with NO network) inside that image.
The image is cached by the dependency list, so later runs are instant.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from backend.repository.manager import IGNORED_DIRS
from backend.services.sandbox_runner import DEFAULT_IMAGE

MAX_PACKAGES = 80
BUILD_TIMEOUT = int(os.getenv("CODE_GUARDIAN_ENV_BUILD_TIMEOUT", "900"))
NOTES_DIR = Path(tempfile.gettempdir()) / "codeguardian-env-notes"
_LOCK = threading.Lock()

# Huge packages that are not worth baking into a sandbox image.
DEFAULT_SKIP = {"torch", "torchvision", "torchaudio", "tensorflow",
                "tensorflow-cpu", "jax", "jaxlib"}

# import name -> pip name. Only imports found here are ever installed from
# source-code scanning (never an arbitrary name: that would allow typosquatting).
IMPORT_TO_PIP = {
    "fastapi": "fastapi", "flask": "flask", "django": "django",
    "sqlalchemy": "sqlalchemy", "pydantic": "pydantic", "uvicorn": "uvicorn",
    "starlette": "starlette", "requests": "requests", "httpx": "httpx",
    "aiohttp": "aiohttp", "jinja2": "jinja2", "werkzeug": "werkzeug",
    "click": "click", "numpy": "numpy", "pandas": "pandas", "scipy": "scipy",
    "sklearn": "scikit-learn", "matplotlib": "matplotlib", "PIL": "pillow",
    "cv2": "opencv-python-headless", "yaml": "pyyaml", "bs4": "beautifulsoup4",
    "jwt": "pyjwt", "dotenv": "python-dotenv", "jose": "python-jose",
    "passlib": "passlib", "bcrypt": "bcrypt", "cryptography": "cryptography",
    "psycopg2": "psycopg2-binary", "pymysql": "pymysql", "redis": "redis",
    "celery": "celery", "boto3": "boto3", "openai": "openai",
    "anthropic": "anthropic", "groq": "groq", "multipart": "python-multipart",
    "email_validator": "email-validator", "markdown": "markdown",
    "lxml": "lxml", "tqdm": "tqdm", "attr": "attrs",
    "dateutil": "python-dateutil", "pymongo": "pymongo", "alembic": "alembic",
    "flask_cors": "flask-cors", "flask_sqlalchemy": "flask-sqlalchemy",
    "flask_login": "flask-login", "pypdf": "pypdf", "PyPDF2": "pypdf2",
    "docx": "python-docx", "websockets": "websockets", "aiofiles": "aiofiles",
    "gunicorn": "gunicorn", "sqlmodel": "sqlmodel", "rich": "rich",
    "typer": "typer", "pytest": "pytest", "itsdangerous": "itsdangerous",
}

_REQ = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[A-Za-z0-9,._-]+\])?"
    r"((?:==|>=|<=|~=|!=|<|>)[A-Za-z0-9.*+!_-]+"
    r"(?:,(?:==|>=|<=|~=|!=|<|>)[A-Za-z0-9.*+!_-]+)*)?$"
)


def canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def base_name(requirement: str) -> str:
    return re.split(r"[\[<>=!~]", requirement, maxsplit=1)[0]


# ---------------------------------------------------------------- parsing

def parse_requirements(text: str) -> list[str]:
    """Keep only plain 'name[extras]==version' lines. Drops options (-r, -e,
    --index-url), URLs, git+ links and local paths, which could pull code
    from places the user did not choose."""
    found = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip().replace(" ", "")
        if line and not line.startswith("-") and _REQ.match(line):
            found.append(line)
    return found


def _requirements_files(root: Path) -> list[Path]:
    files = []
    for pattern in ("requirements*.txt", "*/requirements*.txt", "requirements/*.txt"):
        for path in root.glob(pattern):
            parts = path.relative_to(root).parts[:-1]
            if any(p in IGNORED_DIRS for p in parts):
                continue
            if re.search(r"dev|test|doc|lint", path.name.lower()):
                continue
            files.append(path)
    return sorted(set(files))


def _pyproject_dependencies(root: Path) -> list[str]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return []
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return parse_requirements("\n".join(data.get("project", {}).get("dependencies", [])))
    except Exception:
        return []


def scan_imports(root: Path, limit: int = 2000) -> set[str]:
    """Third-party top-level modules imported by the repo's own code."""
    imported: set[str] = set()
    local: set[str] = set()
    count = 0

    for path in root.rglob("*.py"):
        parts = path.relative_to(root).parts
        if any(p in IGNORED_DIRS or p.endswith(".egg-info") for p in parts[:-1]):
            continue
        count += 1
        if count > limit:
            break
        local.add(path.stem)
        local.update(parts[:-1])
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])

    return {m for m in imported if m not in sys.stdlib_module_names and m not in local}


def _skipped_names() -> set[str]:
    extra = os.getenv("CODE_GUARDIAN_SKIP_PACKAGES", "")
    return DEFAULT_SKIP | {canon(x) for x in extra.split(",") if x.strip()}


def collect_requirements(root: Path) -> tuple[list[str], list[str]]:
    """Return (packages to install, packages skipped on purpose)."""
    wanted: list[str] = []
    for path in _requirements_files(root):
        try:
            wanted += parse_requirements(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    wanted += _pyproject_dependencies(root)

    declared = {canon(base_name(r)) for r in wanted}
    for module in sorted(scan_imports(root)):
        pip_name = IMPORT_TO_PIP.get(module)
        if pip_name and canon(pip_name) not in declared:
            wanted.append(pip_name)
            declared.add(canon(pip_name))
    if "pytest" not in declared:
        wanted.append("pytest")

    skip = _skipped_names()
    keep, skipped, seen = [], [], set()
    for req in wanted:
        name = canon(base_name(req))
        if name in seen:
            continue
        seen.add(name)
        if name in skip or name.startswith("nvidia-"):
            skipped.append(name)
        else:
            keep.append(req)
    return sorted(keep)[:MAX_PACKAGES], sorted(skipped)


# ---------------------------------------------------------------- building

def _install_script(requirements: list[str]) -> str:
    flags = "--no-cache-dir --disable-pip-version-check"
    if os.getenv("CODE_GUARDIAN_ALLOW_SDIST", "0") != "1":
        flags += " --only-binary=:all:"   # wheels only: no setup.py of unknown packages runs
    lines = []
    for req in requirements:
        name = base_name(req)
        # Try the pinned version first, then the latest version, else skip.
        lines.append(
            f"pip install {flags} {shlex.quote(req)} >/dev/null 2>&1 || "
            f"pip install {flags} {shlex.quote(name)} >/dev/null 2>&1 && "
            f"echo 'CG_OK {name}' || echo 'CG_SKIP {name}'"
        )
    return "\n".join(lines) + "\n"


def _image_exists(docker: str, image: str) -> bool:
    return subprocess.run([docker, "image", "inspect", image],
                          capture_output=True, check=False).returncode == 0


def _build(docker: str, base: str, tag: str, requirements: list[str]) -> str:
    with tempfile.TemporaryDirectory(prefix="cg-envbuild-") as tmp:
        ctx = Path(tmp)
        (ctx / "install.sh").write_text(_install_script(requirements), encoding="utf-8")
        (ctx / "Dockerfile").write_text(
            f"FROM {base}\nLABEL cg.env=1\nUSER root\n"
            "COPY install.sh /tmp/install.sh\n"
            "RUN sh /tmp/install.sh && rm /tmp/install.sh\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [docker, "build", "--progress=plain", "-t", tag, str(ctx)],
            capture_output=True, text=True, timeout=BUILD_TIMEOUT, check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-300:].strip())

    output = (proc.stdout or "") + (proc.stderr or "")
    ok = re.findall(r"CG_OK ([A-Za-z0-9._-]+)", output)
    bad = re.findall(r"CG_SKIP ([A-Za-z0-9._-]+)", output)
    note = f"Dependency image built: {len(set(ok))} package(s) installed"
    if bad:
        note += f"; could not install: {', '.join(sorted(set(bad)))}"
    return note + "."


def ensure_repo_image(root: Path) -> tuple[str, str]:
    """Return (image to run the sandbox in, short note for the user).

    Never raises: on any problem it falls back to the base sandbox image."""
    base = os.getenv("CODE_GUARDIAN_SANDBOX_IMAGE", DEFAULT_IMAGE)
    docker = shutil.which("docker")

    if os.getenv("CODE_GUARDIAN_AUTO_ENV", "1") == "0" or not docker:
        return base, ""

    try:
        requirements, skipped = collect_requirements(Path(root))
        digest = hashlib.sha256((base + "\n".join(requirements)).encode()).hexdigest()[:12]
        tag = f"cg-env-{digest}"
        note_file = NOTES_DIR / f"{tag}.txt"

        with _LOCK:   # one build at a time; the next caller finds the cached image
            if _image_exists(docker, tag):
                saved = note_file.read_text(encoding="utf-8") if note_file.is_file() else ""
                return tag, saved
            if not _image_exists(docker, base):
                return base, ""   # the runner reports the missing base image

            note = _build(docker, base, tag, requirements)
            if skipped:
                note += f" Skipped on purpose (too large): {', '.join(skipped)}."
            NOTES_DIR.mkdir(parents=True, exist_ok=True)
            note_file.write_text(note, encoding="utf-8")
            return tag, note
    except Exception as exc:
        return base, (f"Could not build a dependency image "
                      f"({type(exc).__name__}: {exc}); used the base image.")