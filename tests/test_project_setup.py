from pathlib import Path

from core.project_setup import initialize_new_python_project


def test_initializes_safe_python_project(tmp_path: Path) -> None:
    project = tmp_path / "example-project"

    workspace = initialize_new_python_project(project)

    assert workspace.root == project.resolve()
    assert (project / "README.md").is_file()
    assert (project / "pytest.ini").is_file()
    assert (project / "src/__init__.py").is_file()
