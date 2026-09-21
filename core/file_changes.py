from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from agents.builder import BuildProposal
from core.workspace import SafetyError, SafeWorkspace


def _resolve_new_paths(
    workspace: SafeWorkspace,
    proposal: BuildProposal,
) -> list[tuple[Path, str, str]]:
    resolved = [
        (workspace.resolve(change.path), change.path, change.content)
        for change in proposal.files
    ]

    existing = [relative_path for path, relative_path, _ in resolved if path.exists()]
    if existing:
        raise SafetyError(
            "Refusing to overwrite existing file: " + ", ".join(existing)
        )

    return resolved


def create_new_files(
    workspace: SafeWorkspace,
    proposal: BuildProposal,
) -> list[str]:
    """Create approved new files only after every target has passed preflight."""
    resolved = _resolve_new_paths(workspace, proposal)

    for path, _, content in resolved:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return [relative_path for _, relative_path, _ in resolved]


def replace_existing_files(
    workspace: SafeWorkspace,
    proposal: BuildProposal,
) -> list[str]:
    """Atomically replace explicitly approved existing files."""
    resolved = [
        (workspace.resolve(change.path), change.path, change.content)
        for change in proposal.files
    ]
    missing = [
        relative_path for path, relative_path, _ in resolved if not path.is_file()
    ]
    if missing:
        raise SafetyError(
            "Repair can only replace existing files: " + ", ".join(missing)
        )

    for path, _, content in resolved:
        temporary_name: str | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary_name = temporary.name

            Path(temporary_name).replace(path)
        finally:
            if temporary_name:
                temporary_path = Path(temporary_name)
                if temporary_path.exists():
                    temporary_path.unlink()

    return [relative_path for _, relative_path, _ in resolved]
