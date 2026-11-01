"""Dummy environment variables for the sandbox.

Put this file at: backend/services/sandbox_vars.py

Many projects read settings (API keys, DATABASE_URL, SECRET_KEY...) the moment a
module is imported. The sandbox has no .env, so the import fails before the
patch can be tested. This file finds the variable NAMES the repo uses and gives
each a harmless placeholder value. Real secrets are never copied in.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from backend.repository.manager import IGNORED_DIRS

MAX_VARS = 100
_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_BLOCKED = {"PATH", "HOME", "USER", "SHELL", "TMPDIR", "PWD", "LANG"}
_ENV_FILES = (".env", ".env.example", ".env.sample", ".env.template")
_GETTERS = {"getenv", "get"}


def _allowed(name: str) -> bool:
    return bool(_NAME.match(name)) and name not in _BLOCKED and not name.startswith(("LD_", "PYTHON", "DYLD_"))


def _string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _names_from_source(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        # os.getenv("X") / os.environ.get("X") / environ.get("X")
        if isinstance(node, ast.Call) and node.args:
            func = node.func
            attr = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if attr in _GETTERS and (name := _string(node.args[0])):
                found.add(name)
        # os.environ["X"]
        elif isinstance(node, ast.Subscript):
            target = node.value
            if isinstance(target, ast.Attribute) and target.attr == "environ":
                if name := _string(node.slice):
                    found.add(name)
        # class Settings(BaseSettings): DATABASE_URL: str
        elif isinstance(node, ast.ClassDef):
            bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
            if any("Settings" in b for b in bases):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        found.add(item.target.id.upper())
    return found


def _names_from_env_files(root: Path) -> set[str]:
    found: set[str] = set()
    for filename in _ENV_FILES:
        path = root / filename
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    found.add(line.split("=", 1)[0].replace("export ", "").strip())   # name only
        except (OSError, UnicodeDecodeError):
            continue
    return found


def placeholder(name: str) -> str:
    n = name.upper()
    if ("URL" in n or "URI" in n) and any(t in n for t in ("DATABASE", "DB", "SQLALCHEMY")):
        return "sqlite:///:memory:"
    if any(t in n for t in ("PORT", "TIMEOUT", "EXPIRE", "MINUTES", "SECONDS", "DAYS", "LIMIT", "MAX", "SIZE", "TTL")):
        return "30"
    if any(t in n for t in ("DEBUG", "ENABLE", "USE_")):
        return "false"
    return "sandbox-placeholder"


def sandbox_env_vars(root: Path, limit: int = 2000) -> dict[str, str]:
    names = _names_from_env_files(Path(root))
    count = 0
    for path in Path(root).rglob("*.py"):
        parts = path.relative_to(root).parts
        if any(p in IGNORED_DIRS or p.endswith(".egg-info") for p in parts[:-1]):
            continue
        count += 1
        if count > limit:
            break
        try:
            names |= _names_from_source(ast.parse(path.read_text(encoding="utf-8")))
        except (SyntaxError, ValueError, OSError):
            continue

    allowed = sorted(n for n in names if _allowed(n))[:MAX_VARS]
    return {name: placeholder(name) for name in allowed}