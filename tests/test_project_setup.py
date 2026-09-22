from pathlib import Path

import pytest

from core.project_setup import initialize_new_python_project


def test_initializes_safe_python_project(tmp_path: Path) -> None:
    project = tmp_path / "example-project"

    workspace = initialize_new_python_project(project)

    assert workspace.root == project.resolve()
    assert (project / "README.md").is_file()
    assert (project / "pytest.ini").is_file()
    assert (project / "src/__init__.py").is_file()


def test_initializes_fastapi_project_profile(tmp_path: Path) -> None:
    project = tmp_path / "web-product"

    initialize_new_python_project(project, profile="fastapi")

    assert "fastapi" in (project / "requirements.txt").read_text()
    assert (project / ".python-version").read_text() == "3.12\n"
    assert '"entrypoint": "src.main:app"' in (
        project / ".dumbbots/project.json"
    ).read_text()


def test_rejects_unknown_project_profile(tmp_path: Path) -> None:
    project = tmp_path / "unknown"

    with pytest.raises(ValueError, match="Unsupported project profile"):
        initialize_new_python_project(project, profile="node")
