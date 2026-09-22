from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from agents.lead import Ticket, extract_json_object
from core.model import ask_model_json


class ImplementationPlan(BaseModel):
    target_files: list[str] = Field(min_length=1, max_length=5)
    steps: list[str] = Field(min_length=2, max_length=6)
    tests_to_add: list[str] = Field(min_length=1, max_length=5)
    risks: list[str] = Field(default_factory=list, max_length=4)


def validate_plan(plan: ImplementationPlan, profile: str = "library") -> None:
    """Reject plans with unsafe, placeholder, or incomplete file targets."""
    placeholders = {"relative", "path", "file", "todo", "example"}

    for target in plan.target_files:
        path = Path(target)

        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe target path: {target}")

        if any(part.lower() in placeholders for part in path.parts):
            raise ValueError(f"Placeholder target path is not allowed: {target}")

        if path.suffix != ".py":
            raise ValueError(f"Target must be a Python file: {target}")

    if not any("test" in Path(target).name for target in plan.target_files):
        raise ValueError("Plan must include a Python test file.")

    if profile == "fastapi" and set(plan.target_files) != {
        "src/main.py",
        "tests/test_main.py",
    }:
        raise ValueError(
            "FastAPI plans must target src/main.py and tests/test_main.py."
        )


def create_plan(
    ticket: Ticket, existing_files: list[str], profile: str = "library"
) -> ImplementationPlan:
    """Create a minimal plan for one approved ticket without changing code."""
    if profile == "fastapi":
        plan = ImplementationPlan(
            target_files=["src/main.py", "tests/test_main.py"],
            steps=[
                "Create the FastAPI application and health endpoint.",
                "Implement HTTP routes for the approved acceptance criteria.",
                "Validate invalid request data with explicit HTTP responses.",
                "Add API tests for health, success, and rejected inputs.",
            ],
            tests_to_add=ticket.acceptance_criteria[:5],
            risks=["The generated API must preserve the ticket's exact behaviour."],
        )
        validate_plan(plan, profile)
        return plan

    files = "\n".join(f"- {file_name}" for file_name in existing_files) or "- None"

    prompt = f"""
You are Architect Bot in a safe local engineering team.

Create a minimal implementation plan for this approved ticket.
You must not write code, change files, deploy, or expand the scope.

Approved ticket:
Title: {ticket.title}
Summary: {ticket.summary}
Acceptance criteria:
{chr(10).join(f"- {item}" for item in ticket.acceptance_criteria)}

Existing files in the assigned project:
{files}

Rules:
- Use concrete relative Python paths; never use placeholders.
- Include one application Python file and one test Python file.
- Target files must remain inside the assigned project.
- Keep the plan limited to this one ticket.
- Tests must directly cover the acceptance criteria.
""".strip()

    response = ask_model_json(prompt, ImplementationPlan.model_json_schema())
    payload = json.loads(extract_json_object(response))
    plan = ImplementationPlan.model_validate(payload)
    validate_plan(plan, profile)
    return plan
