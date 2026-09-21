from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from agents.lead import Ticket, extract_json_object
from core.model import ask_model_json
from core.workspace import CheckResult


class QaReport(BaseModel):
    decision: Literal["accept", "reject"]
    summary: str = Field(min_length=10, max_length=500)
    findings: list[str] = Field(min_length=1, max_length=6)


def force_reject_on_failed_checks(
    report: QaReport,
    checks: list[CheckResult],
) -> QaReport:
    """A model may not accept work when an approved automated check failed."""
    failed_checks = [check.name for check in checks if check.returncode != 0]

    if not failed_checks:
        return report

    finding = f"Automated checks failed: {', '.join(failed_checks)}."
    return report.model_copy(
        update={
            "decision": "reject",
            "summary": "QA rejected the work because an approved check failed.",
            "findings": [finding, *report.findings],
        }
    )


def evaluate_qa(
    ticket: Ticket,
    source_files: dict[str, str],
    checks: list[CheckResult],
) -> QaReport:
    """Independently assess one implementation against its ticket and evidence."""
    source = "\n\n".join(
        f"--- {path} ---\n{content}" for path, content in source_files.items()
    )
    check_output = "\n\n".join(
        f"{check.name} (exit {check.returncode}):\n{check.output}"
        for check in checks
    )

    prompt = f"""
You are QA Bot in a safe local engineering team.

Independently assess whether the implementation satisfies the ticket.
You may only accept when every acceptance criterion is covered and all
automated checks pass. You must not suggest code changes.

Ticket:
{ticket.title}
{ticket.summary}

Acceptance criteria:
{chr(10).join(f"- {item}" for item in ticket.acceptance_criteria)}

Source files:
{source}

Automated evidence:
{check_output}

Return a concise decision and concrete findings.
""".strip()

    response = ask_model_json(prompt, QaReport.model_json_schema())
    payload = json.loads(extract_json_object(response))

    if not payload.get("findings"):
        payload["findings"] = ["No specific findings were returned by QA."]

    report = QaReport.model_validate(payload)
    return force_reject_on_failed_checks(report, checks)
