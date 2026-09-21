from pathlib import Path

import pytest

from agents.builder import BuildProposal, FileChange
from core.file_changes import create_new_files, replace_existing_files
from core.workspace import SafetyError, SafeWorkspace


def test_creates_approved_new_files_after_preflight(tmp_path: Path) -> None:
    workspace = SafeWorkspace(tmp_path)
    proposal = BuildProposal(
        summary="Create the approved implementation files.",
        files=[
            FileChange(path="src/example.py", content="VALUE = 1\n"),
            FileChange(path="tests/test_example.py", content="pass\n"),
        ],
    )

    assert create_new_files(workspace, proposal) == [
        "src/example.py",
        "tests/test_example.py",
    ]


def test_does_not_partially_write_when_a_target_exists(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("old\n", encoding="utf-8")
    workspace = SafeWorkspace(tmp_path)
    proposal = BuildProposal(
        summary="Attempt to create one new and one existing file.",
        files=[
            FileChange(path="new.py", content="new\n"),
            FileChange(path="existing.py", content="replacement\n"),
        ],
    )

    with pytest.raises(SafetyError, match="overwrite"):
        create_new_files(workspace, proposal)

    assert not (tmp_path / "new.py").exists()
    assert (tmp_path / "existing.py").read_text() == "old\n"


def test_repair_replaces_only_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "example.py"
    target.write_text("old\n", encoding="utf-8")
    workspace = SafeWorkspace(tmp_path)
    proposal = BuildProposal(
        summary="Repair an existing implementation file.",
        files=[FileChange(path="example.py", content="new\n")],
    )

    assert replace_existing_files(workspace, proposal) == ["example.py"]
    assert target.read_text() == "new\n"


def test_repair_refuses_missing_file(tmp_path: Path) -> None:
    workspace = SafeWorkspace(tmp_path)
    proposal = BuildProposal(
        summary="Attempt to repair a missing implementation file.",
        files=[FileChange(path="missing.py", content="new\n")],
    )

    with pytest.raises(SafetyError, match="existing"):
        replace_existing_files(workspace, proposal)
