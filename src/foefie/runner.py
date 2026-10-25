"""Running commands inside a project directory."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer

from foefie.workspace import root


def _run(where: Path, *cmd: str, extra: list[str] | None = None) -> int:
    """Run a command in a project directory and return its exit status.

    A missing directory returns 2 and a missing tool 127, after printing why, so
    callers running several suites can carry on.
    """
    full = [*cmd, *(extra or [])]
    cwd = root() / where
    if not cwd.is_dir():
        typer.secho(f"{where} does not exist", fg=typer.colors.RED, err=True)
        return 2
    if shutil.which(full[0]) is None:
        typer.secho(
            f"{full[0]} not found on PATH. Run `mise install` in {root()}.",
            fg=typer.colors.RED,
            err=True,
        )
        return 127
    typer.secho(f"[{where}] $ {' '.join(full)}", dim=True)
    return subprocess.run(full, cwd=cwd).returncode


def run(where: Path, *cmd: str, extra: list[str] | None = None) -> None:
    """Run a command in a project directory and exit with its status if it fails."""
    code = _run(where, *cmd, extra=extra)
    if code:
        raise typer.Exit(code)
