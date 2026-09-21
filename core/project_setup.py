from __future__ import annotations

from pathlib import Path

from core.workspace import SafeWorkspace

_BASELINE_FILES = {
    "README.md": "# Managed by DumbBots\n",
    "pytest.ini": "[pytest]\npythonpath = .\n",
    "src/__init__.py": "",
}


def initialize_new_python_project(project_path: Path) -> SafeWorkspace:
    """Create a minimal safe Python project only when its directory is new."""
    if project_path.exists():
        return SafeWorkspace(project_path)

    project_path.mkdir(parents=True)

    for relative_path, content in _BASELINE_FILES.items():
        path = project_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return SafeWorkspace(project_path)
