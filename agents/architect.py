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


def validate_plan(plan: ImplementationPlan) -> None:
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


def create_plan(ticket: Ticket, existing_files: list[str]) -> ImplementationPlan:
    """Create a minimal plan for one approved ticket without changing code."""
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
    validate_plan(plan)
    return plan
