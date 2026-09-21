import pytest

from agents.architect import validate_plan
from agents.lead import Ticket
from agents.reviewer import ReviewDecision, force_reject_if_evidence_failed


def test_qa_rejection_forces_reviewer_rejection() -> None:
    qa_report = QaReport(
        decision="reject",
        summary="QA found a failed automated check.",
        findings=["Ruff failed."],
    )
    review = ReviewDecision(
        decision="accept",
        rationale="The implementation looks correct.",
    )

    result = force_reject_if_evidence_failed(review, qa_report, [])

    assert result.decision == "reject"

def test_ticket_requires_testable_fields() -> None:
    ticket = Ticket(
        title="Add minimum stock validator",
        summary="Add a small function that identifies stock below its minimum.",
        acceptance_criteria=[
            "Returns true when quantity is below the minimum.",
            "Negative inputs are rejected.",
        ],
        out_of_scope=["Database storage is not added."],
        suggested_checks=["pytest", "ruff"],
    )

    assert ticket.suggested_checks == ["pytest", "ruff"]
from agents.lead import extract_json_object


def test_extracts_json_from_markdown_fence() -> None:
    response = '```json\n{"title": "Example"}\n```'

    assert extract_json_object(response) == '{"title": "Example"}'
from agents.architect import ImplementationPlan


def test_implementation_plan_has_required_sections() -> None:
    plan = ImplementationPlan(
        target_files=["stock_checker.py", "tests/test_stock_checker.py"],
        steps=["Add the stock check function.", "Add tests for its behaviour."],
        tests_to_add=["Negative values raise ValueError."],
    )

    assert len(plan.target_files) == 2
def test_rejects_placeholder_target_path() -> None:
    plan = ImplementationPlan(
        target_files=["relative/path.py"],
        steps=["Implement the function.", "Add tests."],
        tests_to_add=["Negative values raise ValueError."],
    )

    with pytest.raises(ValueError, match="Placeholder"):
        validate_plan(plan)
from agents.qa import QaReport, force_reject_on_failed_checks
from core.workspace import CheckResult


def test_failed_check_forces_qa_rejection() -> None:
    report = QaReport(
        decision="accept",
        summary="The implementation appears correct.",
        findings=["Behaviour is covered by tests."],
    )
    checks = [CheckResult(name="pytest", returncode=1, output="one test failed")]

    result = force_reject_on_failed_checks(report, checks)

    assert result.decision == "reject"
