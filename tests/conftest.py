import os
import subprocess
from pathlib import Path

import pytest

import foefie

# Build the CLI from the bundled example, never from a foefie.toml in the real workspace.
os.environ["FOEFIE_CONFIG"] = str(Path(foefie.__file__).with_name("foefie.example.toml"))


@pytest.fixture
def calls(monkeypatch):
    """Record subprocess.run calls; each returns the next code from `codes` (default 0)."""
    from foefie import runner

    class Calls(list):
        codes: list[int]

    made = Calls()
    made.codes = []

    def fake_run(cmd, cwd=None, **kwargs):
        made.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, made.codes.pop(0) if made.codes else 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    return made
