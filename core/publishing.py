from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from core.workspace import SafetyError, SafeWorkspace


def find_latest_accepted_report(
    project: str,
    runs_dir: Path = Path("runs"),
) -> Path:
    """Return the newest accepted report for a project."""
    if not runs_dir.is_dir():
        raise SafetyError("No run reports exist. Run review before publishing.")

    for report_path in sorted(runs_dir.glob("*.json"), reverse=True):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        checks = report.get("checks", [])
        accepted = report.get("review", {}).get("decision") == "accept"
        checks_passed = checks and all(check.get("returncode") == 0 for check in checks)

        if report.get("project") == project and accepted and checks_passed:
            return report_path

    raise SafetyError(
        f"No accepted review report with passing checks exists for: {project}"
    )


def validate_publishable_files(workspace: SafeWorkspace) -> None:
    """Block common secret-bearing files from being published."""
    blocked_suffixes = {".key", ".pem", ".p12", ".pfx"}
    blocked_names = {".env", "credentials.json", "service-account.json"}

    unsafe = [
        file_name
        for file_name in workspace.list_files()
        if Path(file_name).name.lower() in blocked_names
        or Path(file_name).suffix.lower() in blocked_suffixes
    ]
    if unsafe:
        raise SafetyError(
            "Refusing to publish possible secret files: " + ", ".join(unsafe)
        )


def _run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        raise SafetyError(output or f"Command failed: {command[0]}")
    return output


def publish_project(
    project: str,
    workspace: SafeWorkspace,
    *,
    public: bool = False,
    runs_dir: Path = Path("runs"),
) -> str:
    """Create and push a dedicated GitHub repository for an accepted project."""
    find_latest_accepted_report(project, runs_dir)
    validate_publishable_files(workspace)

    if shutil.which("git") is None:
        raise SafetyError("Git is not installed.")
    if shutil.which("gh") is None:
        raise SafetyError("GitHub CLI is not installed.")
    if (workspace.root / ".git").exists():
        raise SafetyError("Project already contains a Git repository.")

    visibility = "--public" if public else "--private"
    _run(["git", "init", "-b", "main"], workspace.root)
    _run(["git", "add", "."], workspace.root)
    _run(
        ["git", "commit", "-m", "feat: initial DumbBots-generated project"],
        workspace.root,
    )
    _run(
        [
            "gh",
            "repo",
            "create",
            project,
            visibility,
            "--source=.",
            "--remote=origin",
            "--push",
        ],
        workspace.root,
    )
    return _run(["gh", "repo", "view", "--json", "url", "--jq", ".url"], workspace.root)
