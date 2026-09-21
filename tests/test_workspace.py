from pathlib import Path

import pytest

from core.workspace import SafetyError, SafeWorkspace


def test_lists_and_reads_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    workspace = SafeWorkspace(tmp_path)

    assert workspace.list_files() == ["app.py"]
    assert workspace.read_file("app.py") == "print('hello')"


def test_blocks_paths_outside_project(tmp_path: Path) -> None:
    workspace = SafeWorkspace(tmp_path)

    with pytest.raises(SafetyError, match="escapes"):
        workspace.resolve("../outside.txt")


def test_blocks_unapproved_commands(tmp_path: Path) -> None:
    workspace = SafeWorkspace(tmp_path)

    with pytest.raises(SafetyError, match="not allowed"):
        workspace.run_check("rm")

