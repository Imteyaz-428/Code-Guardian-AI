from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IMAGE = "code-guardian-sandbox:latest"


class SandboxUnavailable(RuntimeError):
    """Docker (or the sandbox image) cannot be used on this machine."""


@dataclass
class SandboxRun:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float


def _to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _make_world_readable(workspace: Path) -> None:
    for current, dirs, files in os.walk(workspace):
        for name in dirs:
            try:
                os.chmod(Path(current) / name, 0o755)
            except OSError:
                pass
        for name in files:
            try:
                os.chmod(Path(current) / name, 0o644)
            except OSError:
                pass
    try:
        os.chmod(workspace, 0o755)
    except OSError:
        pass


class DockerSandbox:
    name = "docker"

    def __init__(self, image=None, memory="512m", cpus="1", pids_limit=128):
        self.image = image or os.getenv("CODE_GUARDIAN_SANDBOX_IMAGE", DEFAULT_IMAGE)
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit
        self._docker = shutil.which("docker")

    def check_ready(self) -> None:
        if not self._docker:
            raise SandboxUnavailable("the 'docker' command was not found")
        try:
            info = subprocess.run([self._docker, "info"], capture_output=True,
                                  timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxUnavailable(f"Docker is not responding: {exc}") from exc
        if info.returncode != 0:
            raise SandboxUnavailable("the Docker daemon is not running (start Docker Desktop)")
        image = subprocess.run([self._docker, "image", "inspect", self.image],
                               capture_output=True, check=False)
        if image.returncode != 0:
            raise SandboxUnavailable(
                f"sandbox image '{self.image}' is missing. Build it with: "
                f"docker build -f docker/Dockerfile.sandbox -t {self.image} ."
            )

    def run(self, workspace: Path, command: list[str], timeout: int) -> SandboxRun:
        workspace = Path(workspace).resolve()
        _make_world_readable(workspace)
        container = f"cg-sandbox-{uuid.uuid4().hex[:12]}"
        # /src is read-only; copy into tmpfs so tests may write files.
        inner = ('mkdir -p /tmp/work && cp -R /src/. /tmp/work '
                 '&& cd /tmp/work && exec "$@"')
        cmd = [
            self._docker, "run", "--rm", "--name", container,
            "--network", "none",
            "--memory", self.memory, "--memory-swap", self.memory,
            "--cpus", self.cpus, "--pids-limit", str(self.pids_limit),
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--read-only", "--tmpfs", "/tmp:rw,exec,size=256m",
            "--user", "65534:65534",
            "--env", "HOME=/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "PYTHONPATH=/tmp/work",
            "-v", f"{workspace}:/src:ro",
            self.image, "sh", "-c", inner, "sh", *command,
        ]
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            subprocess.run([self._docker, "kill", container],
                           capture_output=True, check=False)
            return SandboxRun(-1, _to_text(exc.stdout), _to_text(exc.stderr), True,
                              round(time.monotonic() - start, 3))
        return SandboxRun(proc.returncode, proc.stdout or "", proc.stderr or "", False,
                          round(time.monotonic() - start, 3))


class LocalRunner:
    """NOT a sandbox. Development fallback only (CODE_GUARDIAN_SANDBOX=local)."""

    name = "local-UNSAFE"

    def check_ready(self) -> None:
        return None

    def run(self, workspace: Path, command: list[str], timeout: int) -> SandboxRun:
        cmd = list(command)
        if cmd and cmd[0] == "python":
            cmd[0] = sys.executable
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True,
                                  timeout=timeout, check=False,
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired as exc:
            return SandboxRun(-1, _to_text(exc.stdout), _to_text(exc.stderr), True,
                              round(time.monotonic() - start, 3))
        return SandboxRun(proc.returncode, proc.stdout or "", proc.stderr or "", False,
                          round(time.monotonic() - start, 3))


def get_sandbox_runner():
    """Return a ready runner or raise SandboxUnavailable (fail closed)."""
    mode = os.getenv("CODE_GUARDIAN_SANDBOX", "docker").strip().lower()
    if mode == "local":
        runner = LocalRunner()
    elif mode == "docker":
        runner = DockerSandbox()
    else:
        raise SandboxUnavailable("CODE_GUARDIAN_SANDBOX must be 'docker' or 'local'")
    runner.check_ready()
    return runner