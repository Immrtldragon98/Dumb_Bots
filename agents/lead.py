from __future__ import annotations

import json

from pydantic import BaseModel, Field

from core.model import ask_model_json


class Ticket(BaseModel):
    title: str = Field(min_length=5, max_length=100)
    summary: str = Field(min_length=10, max_length=500)
    acceptance_criteria: list[str] = Field(min_length=2, max_length=6)
    out_of_scope: list[str] = Field(min_length=1, max_length=5)
    suggested_checks: list[str] = Field(min_length=1, max_length=2)


def extract_json_object(response: str) -> str:
    """Extract one JSON object from a model response."""
    start = response.find("{")
    end = response.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("Lead Bot did not return a JSON object.")

    return response[start : end + 1]


def create_ticket(request: str) -> Ticket:
    """Turn one user request into a small, independently verifiable ticket."""
    prompt = f"""
You are the Lead Bot in a safe local engineering team.

Convert the user's request into exactly ONE small engineering ticket.
Do not propose architecture, implementation details, code, deployment, or multiple tickets.

Rules:
- Every acceptance criterion must be testable.
- Suggested checks may contain only "pytest" and/or "ruff".
- Keep the scope realistic for one Builder Bot session.
- Never return an empty out_of_scope list.

User request:
{request}
""".strip()

    response = ask_model_json(prompt, Ticket.model_json_schema())
    payload = json.loads(extract_json_object(response))

    if not payload.get("out_of_scope"):
        payload["out_of_scope"] = [
            "Anything beyond the requested function and its tests is excluded."
        ]

    return Ticket.model_validate(payload)
