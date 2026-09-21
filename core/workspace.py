from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


class SafetyError(ValueError):
    """Raised when an operation violates the DumbBots workspace policy."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    returncode: int
    output: str


class SafeWorkspace:
    """Read-only project access plus approved verification commands."""

    _CHECKS: ClassVar[dict[str, list[str]]] = {
        "pytest": [sys.executable, "-m", "pytest", "-q"],
        "ruff": [sys.executable, "-m", "ruff", "check", "."],
    }

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        if not self.root.is_dir():
            raise SafetyError(f"Project directory does not exist: {root}")

    def resolve(self, relative_path: str) -> Path:
        path = Path(relative_path)

        if path.is_absolute():
            raise SafetyError("Absolute paths are not allowed.")

        resolved = (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            raise SafetyError("Path escapes the assigned project workspace.")

        return resolved

    def list_files(self) -> list[str]:
        ignored = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
        files: list[str] = []

        for path in self.root.rglob("*"):
            if any(part in ignored for part in path.parts):
                continue
            if path.is_file():
                files.append(str(path.relative_to(self.root)))

        return sorted(files)

    def read_file(self, relative_path: str) -> str:
        path = self.resolve(relative_path)

        if not path.is_file():
            raise SafetyError(f"Not a file: {relative_path}")
        if path.stat().st_size > 100_000:
            raise SafetyError("File is too large to read safely.")

        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise SafetyError("Binary files cannot be read as text.") from error

    def run_check(self, name: str) -> CheckResult:
        if name not in self._CHECKS:
            allowed = ", ".join(self._CHECKS)
            raise SafetyError(f"Check '{name}' is not allowed. Allowed: {allowed}")

        completed = subprocess.run(
            self._CHECKS[name],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        output = (completed.stdout + completed.stderr).strip()
        return CheckResult(name=name, returncode=completed.returncode, output=output)
