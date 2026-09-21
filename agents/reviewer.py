from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from agents.lead import Ticket, extract_json_object
from agents.qa import QaReport
from core.model import ask_model_json
from core.workspace import CheckResult


class ReviewDecision(BaseModel):
    decision: Literal["accept", "reject"]
    rationale: str = Field(min_length=10, max_length=500)
    follow_ups: list[str] = Field(default_factory=list, max_length=5)


def force_reject_if_evidence_failed(
    review: ReviewDecision,
    qa_report: QaReport,
    checks: list[CheckResult],
) -> ReviewDecision:
    """Reviewer cannot accept if QA or an approved check rejected the work."""
    failed = [check.name for check in checks if check.returncode != 0]

    if qa_report.decision == "accept" and not failed:
        return review

    reasons = []
    if qa_report.decision == "reject":
        reasons.append("QA rejected the implementation.")
    if failed:
        reasons.append(f"Failed checks: {', '.join(failed)}.")

    return review.model_copy(
        update={
            "decision": "reject",
            "rationale": "Reviewer rejected the work because " + " ".join(reasons),
            "follow_ups": [*reasons, *review.follow_ups],
        }
    )


def review_ticket(
    ticket: Ticket,
    qa_report: QaReport,
    checks: list[CheckResult],
) -> ReviewDecision:
    """Make the final read-only acceptance decision from independent evidence."""
    evidence = "\n".join(
        f"- {check.name}: exit {check.returncode}" for check in checks
    )

    prompt = f"""
You are Reviewer Bot in a safe local engineering team.

Make a final accept or reject decision. You cannot write code or change files.
Accept only when QA accepted, all automated checks passed, and QA findings
show the ticket's acceptance criteria were met.

Ticket:
{ticket.title}
{ticket.summary}

Acceptance criteria:
{chr(10).join(f"- {item}" for item in ticket.acceptance_criteria)}

QA decision: {qa_report.decision}
QA summary: {qa_report.summary}
QA findings:
{chr(10).join(f"- {item}" for item in qa_report.findings)}

Automated checks:
{evidence}
""".strip()

    response = ask_model_json(prompt, ReviewDecision.model_json_schema())
    payload = json.loads(extract_json_object(response))
    review = ReviewDecision.model_validate(payload)
    return force_reject_if_evidence_failed(review, qa_report, checks)
