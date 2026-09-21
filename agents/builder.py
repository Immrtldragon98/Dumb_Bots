from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from agents.architect import ImplementationPlan
from agents.lead import Ticket, extract_json_object
from core.model import ask_model_json
from core.workspace import CheckResult


class FileChange(BaseModel):
    path: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)


class BuildProposal(BaseModel):
    summary: str = Field(min_length=10, max_length=500)
    files: list[FileChange] = Field(min_length=1, max_length=5)


def _validate_paths(paths: list[str]) -> None:
    if len(paths) != len(set(paths)):
        raise ValueError("Builder proposed the same file more than once.")

    for change_path in paths:
        path = Path(change_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe Builder file path: {change_path}")


def _validate_content(proposal: BuildProposal) -> None:
    if any("\x00" in change.content for change in proposal.files):
        raise ValueError("Builder output contains an unsafe null character.")


def validate_proposal(proposal: BuildProposal, plan: ImplementationPlan) -> None:
    """Ensure Builder creates exactly the files approved by Architect."""
    proposed_paths = [change.path for change in proposal.files]
    _validate_paths(proposed_paths)

    if set(proposed_paths) != set(plan.target_files):
        raise ValueError(
            "Builder may only create the exact files approved by Architect."
        )

    _validate_content(proposal)


def validate_repair_proposal(
    proposal: BuildProposal,
    allowed_paths: set[str],
) -> None:
    """Ensure repair changes only known existing Python source files."""
    proposed_paths = [change.path for change in proposal.files]
    _validate_paths(proposed_paths)

    if not set(proposed_paths).issubset(allowed_paths):
        raise ValueError("Repair may only update the listed existing source files.")

    _validate_content(proposal)


def _parse_proposal(response: str) -> BuildProposal:
    payload = json.loads(extract_json_object(response))
    return BuildProposal.model_validate(payload)


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
- Tests must cover all acceptance criteria with correct expected values.
- Do not put Markdown fences inside file content.
""".strip()

    proposal = _parse_proposal(ask_model_json(prompt, BuildProposal.model_json_schema()))
    validate_proposal(proposal, plan)
    return proposal


def propose_repair(
    ticket: Ticket,
    source_files: dict[str, str],
    checks: list[CheckResult],
) -> BuildProposal:
    """Propose a bounded correction after an approved check has failed."""
    allowed_paths = set(source_files)
    source = "\n\n".join(
        f"--- {path} ---\n{content}" for path, content in source_files.items()
    )
    evidence = "\n\n".join(
        f"{check.name} (exit {check.returncode}):\n{check.output}"
        for check in checks
        if check.returncode != 0
    )

    prompt = f"""
You are Builder Bot repairing a failed local Python build.

Correct only the files listed below. Return complete replacement content only
for files that need a correction. Do not create files, delete files, add
packages, or change scope. Make tests express the ticket's acceptance criteria;
never change a test merely to hide a defect.

Ticket:
{ticket.title}
{ticket.summary}

Acceptance criteria:
{chr(10).join(f"- {item}" for item in ticket.acceptance_criteria)}

Existing files you may update:
{chr(10).join(f"- {path}" for path in sorted(allowed_paths))}

Current source:
{source}

Failed automated evidence:
{evidence}

Rules:
- Return at least one corrected file and no other file.
- Keep imports formatted for Ruff.
- Do not put Markdown fences inside file content.
""".strip()

    proposal = _parse_proposal(ask_model_json(prompt, BuildProposal.model_json_schema()))
    validate_repair_proposal(proposal, allowed_paths)
    return proposal
