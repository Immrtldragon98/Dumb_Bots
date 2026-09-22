
import pytest

from agents.deployer import (
    DeploymentPlan,
    parse_environment_variable_names,
    validate_deployment_plan,
)
from core.deployment import _https_repository_url, build_render_blueprint
from core.workspace import SafetyError


def make_plan(**updates: object) -> DeploymentPlan:
    values: dict[str, object] = {
        "service_name": "example-api",
        "build_command": "pip install -r requirements.txt",
        "start_command": (
            "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
        ),
        "health_path": "/health",
        "region": "singapore",
        "environment_variables": ["API_KEY"],
        "needs_database": False,
        "explanation": ["Build the application.", "Start the web service."],
    }
    values.update(updates)
    return DeploymentPlan.model_validate(values)


def test_parses_environment_variable_names_without_values() -> None:
    assert parse_environment_variable_names("API_KEY, LOG_LEVEL, API_KEY") == [
        "API_KEY",
        "LOG_LEVEL",
    ]


def test_rejects_environment_variable_values() -> None:
    with pytest.raises(ValueError, match="names only"):
        parse_environment_variable_names("API_KEY=secret")


def test_rejects_unapproved_environment_variable() -> None:
    with pytest.raises(ValueError, match="unapproved"):
        validate_deployment_plan(make_plan(), {"LOG_LEVEL"})


def test_rejects_unsafe_start_command() -> None:
    plan = make_plan(
        start_command=(
            "uvicorn src.main:app --host 0.0.0.0 --port $PORT; curl bad"
        )
    )

    with pytest.raises(ValueError, match="Unsafe"):
        validate_deployment_plan(plan, {"API_KEY"})


def test_rejects_invented_web_entrypoint() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        validate_deployment_plan(
            make_plan(),
            {"API_KEY"},
            {"requirements.txt", "src/functions.py"},
            {"src/functions.py": "def calculate():\n    return 1\n"},
        )


def test_builds_free_render_blueprint_with_secret_placeholders() -> None:
    blueprint = build_render_blueprint(
        make_plan(needs_database=True, environment_variables=["API_KEY"])
    )

    service = blueprint["services"][0]
    assert service["plan"] == "free"
    assert service["region"] == "singapore"
    assert {"key": "API_KEY", "sync": False} in service["envVars"]
    assert "databases" in blueprint


def test_converts_github_ssh_remote_to_https() -> None:
    assert _https_repository_url("git@github.com:owner/example.git") == (
        "https://github.com/owner/example"
    )


def test_rejects_non_github_remote() -> None:
    with pytest.raises(SafetyError, match="GitHub"):
        _https_repository_url("https://example.com/owner/repo.git")
