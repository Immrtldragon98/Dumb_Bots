import json
from pathlib import Path

import pytest

from core.publishing import (
    find_latest_accepted_report,
    validate_publishable_files,
)
from core.workspace import SafetyError, SafeWorkspace


def write_report(
    path: Path,
    *,
    project: str,
    decision: str,
    returncode: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "project": project,
                "review": {"decision": decision},
                "checks": [{"name": "pytest", "returncode": returncode}],
            }
        ),
        encoding="utf-8",
    )


def test_finds_latest_accepted_report(tmp_path: Path) -> None:
    write_report(
        tmp_path / "20260921T000000Z-old.json",
        project="example",
        decision="reject",
        returncode=1,
    )
    accepted = tmp_path / "20260922T000000Z-new.json"
    write_report(
        accepted,
        project="example",
        decision="accept",
        returncode=0,
    )

    assert find_latest_accepted_report("example", tmp_path) == accepted


def test_rejects_project_without_accepted_report(tmp_path: Path) -> None:
    write_report(
        tmp_path / "20260921T000000Z-report.json",
        project="example",
        decision="reject",
        returncode=0,
    )

    with pytest.raises(SafetyError, match="No accepted review"):
        find_latest_accepted_report("example", tmp_path)


def test_blocks_common_secret_files(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    workspace = SafeWorkspace(tmp_path)

    with pytest.raises(SafetyError, match="secret files"):
        validate_publishable_files(workspace)


def test_allows_normal_project_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    validate_publishable_files(SafeWorkspace(tmp_path))
