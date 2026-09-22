from __future__ import annotations

import json
from pathlib import Path

from core.workspace import SafeWorkspace

_BASELINE_FILES = {
    "README.md": "# Managed by DumbBots\n",
    "pytest.ini": "[pytest]\npythonpath = .\n",
    "src/__init__.py": "",
}

_FASTAPI_FILES = {
    "requirements.txt": (
        "fastapi>=0.115,<1\n"
        "httpx>=0.27,<1\n"
        "uvicorn[standard]>=0.30,<1\n"
    ),
    ".python-version": "3.12\n",
    ".dumbbots/project.json": json.dumps(
        {"profile": "fastapi", "entrypoint": "src.main:app", "health_path": "/health"},
        indent=2,
    ) + "\n",
}


def initialize_new_python_project(
    project_path: Path, profile: str = "library"
) -> SafeWorkspace:
    """Create a minimal safe Python project only when its directory is new."""
    if project_path.exists():
        return SafeWorkspace(project_path)

    if profile not in {"library", "fastapi"}:
        raise ValueError(f"Unsupported project profile: {profile}")

    project_path.mkdir(parents=True)

    baseline = dict(_BASELINE_FILES)
    if profile == "fastapi":
        baseline.update(_FASTAPI_FILES)

    for relative_path, content in baseline.items():
        path = project_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return SafeWorkspace(project_path)
