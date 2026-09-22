from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from agents.lead import extract_json_object
from core.model import ask_model_json


class DeploymentAnswers(BaseModel):
    audience: Literal["public", "private"]
    needs_database: bool
    environment_variables: list[str] = Field(default_factory=list, max_length=20)
    region: Literal["singapore", "frankfurt", "oregon", "ohio", "virginia"]


class DeploymentPlan(BaseModel):
    provider: Literal["render"] = "render"
    service_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")
    service_type: Literal["web"] = "web"
    runtime: Literal["python"] = "python"
    build_command: str = Field(min_length=3, max_length=200)
    start_command: str = Field(min_length=3, max_length=200)
    health_path: str = Field(pattern=r"^/[A-Za-z0-9_./-]*$")
    region: Literal["singapore", "frankfurt", "oregon", "ohio", "virginia"]
    environment_variables: list[str] = Field(default_factory=list, max_length=20)
    needs_database: bool = False
    explanation: list[str] = Field(min_length=2, max_length=8)


def parse_environment_variable_names(value: str) -> list[str]:
    """Parse names only; values and shell syntax are forbidden."""
    if not value.strip():
        return []

    names = [item.strip() for item in value.split(",") if item.strip()]
    invalid = [name for name in names if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name)]
    if invalid:
        raise ValueError(
            "Environment variables must be uppercase names only; do not enter values: "
            + ", ".join(invalid)
        )
    return list(dict.fromkeys(names))


def validate_deployment_plan(
    plan: DeploymentPlan,
    allowed_environment_variables: set[str],
    project_files: set[str] | None = None,
    source_files: dict[str, str] | None = None,
) -> None:
    """Keep model output inside the supported Render Python profile."""
    if not set(plan.environment_variables).issubset(allowed_environment_variables):
        raise ValueError("Deployment Bot introduced an unapproved environment variable.")

    if not (
        plan.build_command == "pip install -r requirements.txt"
        or plan.build_command == "pip install ."
    ):
        raise ValueError("Unsupported Python build command proposed by Deployment Bot.")

    allowed_start_prefixes = ("uvicorn ", "gunicorn ")
    if not plan.start_command.startswith(allowed_start_prefixes):
        raise ValueError("Unsupported Python start command proposed by Deployment Bot.")

    forbidden = (";", "&&", "||", "`", "$(", ">", "<", "\n", "\r")
    if any(token in plan.start_command for token in forbidden):
        raise ValueError("Unsafe shell syntax in Deployment Bot start command.")
    if "0.0.0.0" not in plan.start_command or "$PORT" not in plan.start_command:
        raise ValueError("Web service must bind to 0.0.0.0:$PORT.")

    if project_files is not None:
        expected_build = (
            "pip install -r requirements.txt"
            if "requirements.txt" in project_files
            else "pip install ."
        )
        if plan.build_command != expected_build:
            raise ValueError("Build command does not match the project files.")

    if source_files is not None:
        parts = plan.start_command.split()
        if len(parts) < 2 or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*",
            parts[1],
        ):
            raise ValueError("Deployment Bot returned an invalid application entrypoint.")

        module, application = parts[1].split(":", maxsplit=1)
        source_path = module.replace(".", "/") + ".py"
        if source_path not in source_files:
            raise ValueError(f"Web entrypoint does not exist: {source_path}")
        if not re.search(
            rf"\b{re.escape(application)}\s*=",
            source_files[source_path],
        ):
            raise ValueError(
                f"Web application object '{application}' was not found in {source_path}."
            )


def create_deployment_plan(
    project: str,
    source_files: dict[str, str],
    project_files: list[str],
    answers: DeploymentAnswers,
) -> DeploymentPlan:
    """Create one constrained Render deployment plan from source and answers."""
    source = "\n\n".join(
        f"--- {path} ---\n{content}" for path, content in source_files.items()
    )
    files = "\n".join(f"- {path}" for path in project_files)
    env_names = ", ".join(answers.environment_variables) or "None"

    prompt = f"""
You are Deployment Bot for a safe local engineering team.

Analyze this accepted Python project and create a Render web-service plan.
Return a plan only when the source contains a real ASGI or WSGI web application.
Do not invent files, dependencies, environment variables, or commands.
Never request or return secret values.

Project: {project}
Audience: {answers.audience}
Needs PostgreSQL: {answers.needs_database}
Approved environment variable names: {env_names}
Region: {answers.region}

Project files:
{files}

Python source:
{source}

Rules:
- Provider must be render, service type web, runtime python.
- Use plan-compatible commands only.
- Build command must be exactly "pip install -r requirements.txt" when that
  file exists, otherwise exactly "pip install .".
- Start command must use uvicorn or gunicorn and bind to 0.0.0.0:$PORT.
- Prefer /health when the application defines it; otherwise use /.
- Include only approved environment variable names.
- Explain the plan in simple step-by-step language.
""".strip()

    response = ask_model_json(prompt, DeploymentPlan.model_json_schema())
    payload = json.loads(extract_json_object(response))
    plan = DeploymentPlan.model_validate(payload)
    validate_deployment_plan(
        plan,
        set(answers.environment_variables),
        set(project_files),
        source_files,
    )
    return plan
