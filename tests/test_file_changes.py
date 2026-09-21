from pathlib import Path

import pytest

from agents.builder import BuildProposal, FileChange
from core.file_changes import create_new_files
from core.workspace import SafetyError, SafeWorkspace


def test_creates_approved_new_file(tmp_path: Path) -> None:
    workspace = SafeWorkspace(tmp_path)
    proposal = BuildProposal(
        summary="Create the approved implementation file.",
        files=[FileChange(path="src/example.py", content="VALUE = 1\n")],
    )

    assert create_new_files(workspace, proposal) == ["src/example.py"]
    assert (tmp_path / "src/example.py").read_text() == "VALUE = 1\n"


def test_refuses_to_overwrite_file(tmp_path: Path) -> None:
    target = tmp_path / "example.py"
    target.write_text("old\n", encoding="utf-8")
    workspace = SafeWorkspace(tmp_path)
    proposal = BuildProposal(
        summary="Attempt to replace an existing file.",
        files=[FileChange(path="example.py", content="new\n")],
    )

    with pytest.raises(SafetyError, match="overwrite"):
        create_new_files(workspace, proposal)
