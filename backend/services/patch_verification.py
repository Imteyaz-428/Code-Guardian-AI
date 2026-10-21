from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    status: str
    syntax_passed: bool
    tests_run: bool
    tests_passed: bool | None
    duration_seconds: float
    stdout: str = ""
    stderr: str = ""
    message: str = ""


class PatchVerificationService:
    """Validate proposed Python code in a disposable workspace.

    WARNING:
    This is a temporary-workspace test runner, NOT an OS/container sandbox.
    Pytest can execute arbitrary code with the current user's permissions.
    Only use trusted repositories until proper isolation is implemented.
    """

    IGNORED_PATTERNS = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "datasets",
        "artifacts",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    )

    @staticmethod
    def _ignore_patterns(directory: str, names: list[str]) -> set[str]:
        """Return directory/file names that should be excluded from copying."""
        del directory

        ignored = set(PatchVerificationService.IGNORED_PATTERNS)
        return {name for name in names if name in ignored}

    def verify(
        self,
        repository_root: str | Path,
        relative_file: str,
        proposed_source: str,
        *,
        run_tests: bool = True,
        timeout_seconds: int = 60,
    ) -> dict:
        root = Path(repository_root).expanduser().resolve()

        if not root.is_dir():
            raise ValueError("Repository root is not a directory.")

        rel = Path(relative_file)

        if (
            rel.is_absolute()
            or ".." in rel.parts
            or rel.suffix != ".py"
        ):
            raise ValueError(
                "file_path must be a safe relative Python path."
            )

        original = (root / rel).resolve()

        try:
            original.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                "Target file is outside the repository."
            ) from exc

        if not original.is_file():
            raise FileNotFoundError(
                f"Target file not found: {relative_file}"
            )

        if len(proposed_source) > 1_000_000:
            raise ValueError(
                "Proposed source exceeds the 1 MB limit."
            )

        start = time.monotonic()

        # Step 1: Validate Python syntax.
        try:
            ast.parse(
                proposed_source,
                filename=relative_file,
            )

        except SyntaxError as exc:
            return asdict(
                VerificationResult(
                    status="rejected",
                    syntax_passed=False,
                    tests_run=False,
                    tests_passed=None,
                    duration_seconds=round(
                        time.monotonic() - start, 3
                    ),
                    message=(
                        f"Syntax validation failed: {exc.msg} "
                        f"(line {exc.lineno})."
                    ),
                )
            )

        # Step 2: Return after syntax validation if tests are disabled.
        if not run_tests:
            return asdict(
                VerificationResult(
                    status="syntax_passed",
                    syntax_passed=True,
                    tests_run=False,
                    tests_passed=None,
                    duration_seconds=round(
                        time.monotonic() - start, 3
                    ),
                    message=(
                        "Syntax passed. Tests were not run; "
                        "this is not a verified patch."
                    ),
                )
            )

        # Step 3: Create a disposable repository copy.
        with tempfile.TemporaryDirectory(
            prefix="codeguardian-verify-"
        ) as temp:

            workspace = Path(temp) / "repo"

            shutil.copytree(
                root,
                workspace,
                ignore=self._ignore_patterns,
                symlinks=False,
            )

            # Step 4: Validate the staged file path.
            staged = (workspace / rel).resolve()

            try:
                staged.relative_to(workspace.resolve())

            except ValueError as exc:
                raise ValueError(
                    "Target file escaped the temporary workspace."
                ) from exc

            # Step 5: Replace the file only in the temporary copy.
            staged.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            staged.write_text(
                proposed_source,
                encoding="utf-8",
            )

            # Step 6: Discover Python test files throughout the repository.
            test_files = [
                file
                for file in workspace.rglob("*.py")
                if file.is_file()
                and (
                    file.name.startswith("test_")
                    or file.name.endswith("_test.py")
                )
                and not any(
                    part in self.IGNORED_PATTERNS
                    for part in file.relative_to(workspace).parts
                )
            ]

            if not test_files:
                return asdict(
                    VerificationResult(
                        status="syntax_passed",
                        syntax_passed=True,
                        tests_run=False,
                        tests_passed=None,
                        duration_seconds=round(time.monotonic() - start, 3),
                        message=(
                            "Syntax passed, but no Python test files "
                            "were found. Patch is not verified."
                        ),
                    )
                )

            timeout = max(5, min(int(timeout_seconds), 180))

            # Step 7: Collect tests before running them.
            try:
                collection = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "--collect-only",
                        "-q",
                    ],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    env={
                        **os.environ,
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )

            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""

                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")

                return asdict(
                    VerificationResult(
                        status="rejected",
                        syntax_passed=True,
                        tests_run=True,
                        tests_passed=False,
                        duration_seconds=round(time.monotonic() - start, 3),
                        stdout=stdout[-12000:],
                        stderr=stderr[-12000:],
                        message="Test collection timed out; patch was not verified.",
                    )
                )

            import re

            collection_output = collection.stdout + "\n" + collection.stderr

            count_match = re.search(
                r"(?m)^\s*(\d+)\s+tests?\s+collected\b",
                collection_output,
            )

            collected_count = int(count_match.group(1)) if count_match else 0

            if collection.returncode != 0 or collected_count == 0:
                return asdict(
                    VerificationResult(
                        status="rejected",
                        syntax_passed=True,
                        tests_run=True,
                        tests_passed=False,
                        duration_seconds=round(time.monotonic() - start, 3),
                        stdout=collection.stdout[-12000:],
                        stderr=collection.stderr[-12000:],
                        message=(
                            "Pytest did not successfully collect at least "
                            "one test. Patch is not verified."
                        ),
                    )
                )

            # Step 8: Execute pytest and require a confirmed passing summary.
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                    ],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    env={
                        **os.environ,
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )

            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""

                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")

                return asdict(
                    VerificationResult(
                        status="rejected",
                        syntax_passed=True,
                        tests_run=True,
                        tests_passed=False,
                        duration_seconds=round(time.monotonic() - start, 3),
                        stdout=stdout[-12000:],
                        stderr=stderr[-12000:],
                        message="Test suite timed out; patch was not verified.",
                    )
                )

            summary = proc.stdout + "\n" + proc.stderr

            passed_summary = re.search(
                r"(?m)^\s*\d+\s+passed(?:,|\s|$)",
                summary,
            ) is not None
            passed = proc.returncode == 0 and passed_summary

            return asdict(
                VerificationResult(
                    status="verified" if passed else "rejected",
                    syntax_passed=True,
                    tests_run=True,
                    tests_passed=passed,
                    duration_seconds=round(time.monotonic() - start, 3),
                    stdout=proc.stdout[-12000:],
                    stderr=proc.stderr[-12000:],
                    message=(
                        "Syntax and collected tests passed in a disposable "
                        "copy. Review the diff before applying."
                        if passed
                        else
                        "Tests failed, or pytest did not confirm a passing "
                        "test summary. Do not apply this patch."
                    ),
                )
            )