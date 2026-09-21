from __future__ import annotations

from agents.builder import BuildProposal
from core.workspace import SafetyError, SafeWorkspace


def create_new_files(
    workspace: SafeWorkspace,
    proposal: BuildProposal,
) -> list[str]:
    """Create approved new files; overwriting an existing file is forbidden."""
    written: list[str] = []

    for change in proposal.files:
        path = workspace.resolve(change.path)

        if path.exists():
            raise SafetyError(f"Refusing to overwrite existing file: {change.path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(change.content, encoding="utf-8")
        written.append(change.path)

    return written
