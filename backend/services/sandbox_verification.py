from __future__ import annotations

import ast
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from backend.services.sandbox_runner import SandboxUnavailable, get_sandbox_runner
from backend.services.security_rescan import SecurityRescanService

IGNORED = {
    ".git", ".venv", "venv", "node_modules", "datasets", "artifacts",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".codeguardian-tmp",
}
_FAIL = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)", re.MULTILINE)
_SUMMARY = re.compile(r"\b\d+\s+(?:passed|failed|errors?|skipped|xfailed|xpassed)\b")
_SMOKE = (
    "import importlib, sys\n"
    "try:\n    importlib.import_module(sys.argv[1])\n"
    "except BaseException as e:\n    print('IMPORT_ERROR:', type(e).__name__, str(e)); sys.exit(3)\n"
    "print('IMPORT_OK')\n"
)


def parse_failures(output: str) -> set[str]:
    return set(_FAIL.findall(output))


def module_name(rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _ignore(_d: str, names: list[str]) -> set[str]:
    return {n for n in names if n in IGNORED}


class SandboxVerificationService:
    """verified = syntax OK + no test regressions in a Docker sandbox
    (or module still imports when there are no tests) + no new/unfixed
    security findings in a static re-scan."""

    def _checks(self, runner, workspace: Path, rel: Path, timeout: int) -> dict:
        tests = workspace / "tests"
        if tests.is_dir() and (any(tests.rglob("test_*.py")) or any(tests.rglob("*_test.py"))):
            run = runner.run(workspace, ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                         "--tb=short", "-rfE", "tests"], timeout)
            return {"level": "tests", "run": run, "failures": parse_failures(run.stdout),
                    "ran": bool(_SUMMARY.search(run.stdout)),
                    "no_pytest": "No module named pytest" in run.stdout + run.stderr}
        run = runner.run(workspace, ["python", "-c", _SMOKE, module_name(rel)], timeout)
        return {"level": "smoke", "run": run, "failures": set(), "ran": True,
                "import_ok": run.exit_code == 0 and "IMPORT_OK" in run.stdout}

    def verify(self, repository_root, relative_file: str, proposed_source: str, *,
               timeout_seconds: int = 90, rule_id: str | None = None,
               function_name: str | None = None) -> dict[str, Any]:
        root = Path(repository_root).resolve()
        rel = Path(relative_file)
        if rel.is_absolute() or ".." in rel.parts or rel.suffix != ".py":
            raise ValueError("file_path must be a safe relative Python path.")
        if not (root / rel).is_file():
            raise FileNotFoundError(f"Target file not found: {relative_file}")
        start = time.monotonic()

        def out(status, message, level="none", sandbox="none", run=None, **extra):
            return {
                "status": status, "message": message, "verification_level": level,
                "sandbox": sandbox, "duration_seconds": round(time.monotonic() - start, 3),
                "stdout": (run.stdout if run else "")[-12000:],
                "stderr": (run.stderr if run else "")[-12000:],
                "regressions": extra.pop("regressions", []), "security": extra.pop("security", None),
            }

        try:
            ast.parse(proposed_source, filename=relative_file)
        except SyntaxError as exc:
            return out("rejected", f"Syntax error: {exc.msg} (line {exc.lineno}).")

        try:
            runner = get_sandbox_runner()
        except SandboxUnavailable as exc:
            return out("syntax_passed", f"Sandbox unavailable: {exc}. Patch is NOT verified.",
                       sandbox="unavailable")

        timeout = max(5, min(int(timeout_seconds), 180))
        with tempfile.TemporaryDirectory(prefix="codeguardian-verify-") as tmp:
            ws = Path(tmp) / "repo"
            shutil.copytree(root, ws, ignore=_ignore, symlinks=False)
            base = self._checks(runner, ws, rel, timeout)       # original code
            (ws / rel).write_text(proposed_source, encoding="utf-8")
            new = self._checks(runner, ws, rel, timeout)        # patched code

        run, level, sb = new["run"], new["level"], runner.name
        if run.timed_out:
            return out("rejected", "Sandbox run timed out.", level, sb, run)

        if level == "tests":
            if new["no_pytest"] or not new["ran"]:
                return out("syntax_passed", "pytest did not run in the sandbox image. "
                           "Patch is NOT verified.", level, sb, run)
            regressions = sorted(new["failures"] - base["failures"])
            if regressions:
                return out("rejected", f"Patch breaks {len(regressions)} test(s) that passed before.",
                           level, sb, run, regressions=regressions)
            if run.exit_code not in (0, 1) and run.exit_code != base["run"].exit_code:
                return out("rejected", f"pytest exited with code {run.exit_code}.", level, sb, run)
        elif not new["import_ok"]:
            if base["import_ok"]:
                return out("rejected", "The patched module no longer imports.", level, sb, run)
            # Original bhi import nahi hota -> smoke check kuch prove nahi karta.
            return out("syntax_passed",
                       "The module cannot be imported in the sandbox even before the patch "
                       "(usually missing dependencies in the sandbox image, or imports that "
                       "do not resolve from the repo root). Patch is NOT verified. Rebuild the "
                       "image with --build-arg EXTRA_PIP=\"<repo dependencies>\" or add tests/.",
                       level, sb, run)

        sec = SecurityRescanService().compare(root, relative_file, proposed_source,
                                              rule_id=rule_id, function_name=function_name)
        if not sec["available"]:
            if os.getenv("CODE_GUARDIAN_REQUIRE_RESCAN", "1") != "0":
                return out("syntax_passed", f"Security re-scan could not run ({sec.get('error')}). "
                           "Patch is NOT verified.", level, sb, run, security=sec)
        elif sec["introduced"]:
            return out("rejected", "The patch introduces new security findings.", level, sb, run, security=sec)
        elif rule_id and sec["fix_confirmed"] is False:
            return out("rejected", f"The {rule_id} finding is still detected after the patch.",
                       level, sb, run, security=sec)

        mode = "Docker sandbox" if sb == "docker" else "LOCAL DEV MODE (not isolated)"
        what = "original tests still pass" if level == "tests" else "module imports (no tests/ folder)"
        return out("verified", f"Verified in {mode}: {what}; no new security findings.",
                   level, sb, run, security=sec)