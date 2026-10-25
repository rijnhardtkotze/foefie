"""Locating the ~/code workspace root."""
from __future__ import annotations

from functools import cache
from pathlib import Path

MARKER = "dev.code-workspace"


def find_root(module: Path | None = None) -> Path:
    """The workspace root: the nearest parent holding dev.code-workspace.

    Search up from the current directory first, so a non-editable install still
    finds the workspace it is run from. Fall back to this file's location.
    """
    module = (module or Path(__file__)).resolve()
    start = Path.cwd().resolve()
    for parent in [start, *start.parents, *module.parents]:
        if (parent / MARKER).is_file():
            return parent
    raise SystemExit(f"{MARKER} not found above {start} or {module}")


@cache
def root() -> Path:
    return find_root()
