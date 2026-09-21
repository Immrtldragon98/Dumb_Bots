from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from agents.architect import ImplementationPlan
from agents.lead import Ticket, extract_json_object
from core.model import ask_model_json


class FileChange(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)


class BuildProposal(BaseModel):
    summary: str = Field(min_length=10, max_length=500)
    files: list[FileChange] = Field(min_length=1, max_length=5)


def validate_proposal(
    proposal: BuildProposal,
    plan: ImplementationPlan,
) -> None:
    """Ensure Builder changes exactly the files approved by Architect."""
    expected_paths = set(plan.target_files)
    proposed_paths = [change.path for change in proposal.files]

    if len(proposed_paths) != len(set(proposed_paths)):
        raise ValueError("Builder proposed the same file more than once.")

    if set(proposed_paths) != expected_paths:
        raise ValueError(
            "Builder may only create the exact files approved by Architect."
        )

    for change in proposal.files:
        path = Path(change.path)

        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe Builder file path: {change.path}")

        if "\x00" in change.content:
            raise ValueError("Builder output contains an unsafe null character.")


def propose_build(ticket: Ticket, plan: ImplementationPlan) -> BuildProposal:
    """Generate implementation files for one approved plan."""
    prompt = f"""
You are Builder Bot in a safe local engineering team.

Implement exactly this approved ticket and plan. Return complete Python files.
Do not create extra files, use external packages, deploy, delete files, or change scope.

Ticket:
{ticket.title}
{ticket.summary}

Acceptance criteria:
{chr(10).join(f"- {item}" for item in ticket.acceptance_criteria)}

Approved target files:
{chr(10).join(f"- {item}" for item in plan.target_files)}

Implementation steps:
{chr(10).join(f"- {item}" for item in plan.steps)}

Rules:
- Return content for every approved target file and no other file.
- Use only Python standard library plus pytest in test files.
- Tests must cover all acceptance criteria.
- Do not put Markdown fences inside file content.
""".strip()

    response = ask_model_json(prompt, BuildProposal.model_json_schema())
    payload = json.loads(extract_json_object(response))
    proposal = BuildProposal.model_validate(payload)
    validate_proposal(proposal, plan)
    return proposal
