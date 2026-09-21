from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agents.lead import Ticket
from agents.qa import QaReport
from agents.reviewer import ReviewDecision
from core.workspace import CheckResult


def write_run_report(
    project: str,
    request: str,
    ticket: Ticket,
    qa_report: QaReport,
    review: ReviewDecision,
    checks: list[CheckResult],
    runs_dir: Path | None = None,
) -> Path:
    """Write immutable evidence for one completed DumbBots run."""
    directory = runs_dir or Path("runs")
    directory.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(UTC)
    run_id = f"{created_at:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    report_path = directory / f"{run_id}.json"

    report = {
        "run_id": run_id,
        "created_at": created_at.isoformat(),
        "project": project,
        "request": request,
        "ticket": ticket.model_dump(),
        "qa_report": qa_report.model_dump(),
        "review": review.model_dump(),
        "checks": [asdict(check) for check in checks],
    }

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report_path
