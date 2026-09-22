from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import quote

import yaml

from agents.deployer import DeploymentPlan
from core.publishing import find_latest_accepted_report
from core.workspace import SafetyError, SafeWorkspace


def _https_repository_url(remote: str) -> str:
    remote = remote.strip()
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.removeprefix("git@github.com:")
    remote = remote.removesuffix(".git")
    if not remote.startswith("https://github.com/"):
        raise SafetyError("Deployment Bot currently supports GitHub repositories only.")
    return remote


def get_repository_url(workspace: SafeWorkspace) -> str:
    """Read the project's existing GitHub origin without changing it."""
    completed = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=workspace.root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        raise SafetyError(
            "Project must be published to GitHub before online deployment."
        )
    return _https_repository_url(completed.stdout)


def _run_git(command: list[str], workspace: SafeWorkspace) -> None:
    completed = subprocess.run(
        command,
        cwd=workspace.root,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        raise SafetyError(output or "Git command failed.")


def build_render_blueprint(plan: DeploymentPlan) -> dict[str, object]:
    """Convert a validated plan into a free-tier Render Blueprint."""
    environment_variables: list[dict[str, object]] = []

    if plan.needs_database:
        environment_variables.append(
            {
                "key": "DATABASE_URL",
                "fromDatabase": {
                    "name": f"{plan.service_name}-db",
                    "property": "connectionString",
                },
            }
        )

    environment_variables.extend(
        {"key": name, "sync": False}
        for name in plan.environment_variables
        if name != "DATABASE_URL"
    )

    service: dict[str, object] = {
        "type": "web",
        "name": plan.service_name,
        "runtime": "python",
        "plan": "free",
        "region": plan.region,
        "buildCommand": plan.build_command,
        "startCommand": plan.start_command,
        "healthCheckPath": plan.health_path,
        "autoDeploy": True,
    }
    if environment_variables:
        service["envVars"] = environment_variables

    blueprint: dict[str, object] = {"services": [service]}
    if plan.needs_database:
        blueprint["databases"] = [
            {
                "name": f"{plan.service_name}-db",
                "databaseName": plan.service_name.replace("-", "_"),
                "plan": "free",
                "ipAllowList": [],
            }
        ]
    return blueprint


def write_deployment_files(
    project: str,
    workspace: SafeWorkspace,
    plan: DeploymentPlan,
    runs_dir: Path = Path("runs"),
) -> tuple[list[str], str]:
    """Write reviewed deployment configuration for an accepted project."""
    find_latest_accepted_report(project, runs_dir)
    repository_url = get_repository_url(workspace)

    targets = ["render.yaml", ".dumbbots/deployment.json"]
    existing = [name for name in targets if workspace.resolve(name).exists()]
    if existing:
        raise SafetyError(
            "Deployment configuration already exists: " + ", ".join(existing)
        )

    blueprint = build_render_blueprint(plan)
    render_path = workspace.resolve("render.yaml")
    manifest_path = workspace.resolve(".dumbbots/deployment.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    render_path.write_text(
        yaml.safe_dump(blueprint, sort_keys=False),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(plan.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )

    deeplink = (
        "https://dashboard.render.com/blueprint/new?repo="
        + quote(repository_url, safe="")
    )
    return targets, deeplink


def push_deployment_files(workspace: SafeWorkspace) -> None:
    """Commit and push only Deployment Bot-owned configuration files."""
    _run_git(
        ["git", "add", "render.yaml", ".dumbbots/deployment.json"],
        workspace,
    )
    _run_git(
        ["git", "commit", "-m", "chore: add Render deployment configuration"],
        workspace,
    )
    _run_git(["git", "push", "origin", "HEAD"], workspace)
