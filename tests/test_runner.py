import subprocess

import pytest
from typer.testing import CliRunner

from foefie import runner
from foefie.cli import app

cli = CliRunner()


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A fake workspace with every project directory present and no real commands run."""
    for where in ("mantlepin/rudderpin", "mantlepin-labs/rea-remote/companion"):
        (tmp_path / where).mkdir(parents=True)
    monkeypatch.setattr(runner, "root", lambda: tmp_path)
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/bin/{name}")
    return tmp_path


@pytest.fixture
def calls(monkeypatch):
    """Record subprocess.run calls; each returns the next code from `codes` (default 0)."""
    class Calls(list):
        codes: list[int]

    made = Calls()
    made.codes = []

    def fake_run(cmd, cwd=None, **kwargs):
        made.append((cmd, cwd))
        return subprocess.CompletedProcess(cmd, made.codes.pop(0) if made.codes else 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    return made


def test_run_missing_dir_exits_2(ws, calls):
    result = cli.invoke(app, ["website", "dev"])
    assert result.exit_code == 2
    assert "mantlepin/website does not exist" in result.output
    assert calls == []


def test_run_missing_tool_exits_127(ws, calls, monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: None)
    result = cli.invoke(app, ["rudderpin", "sync"])
    assert result.exit_code == 127
    assert "uv not found on PATH" in result.output
    assert "mise install" in result.output
    assert calls == []


def test_run_propagates_exit_code(ws, calls):
    calls.codes.append(5)
    result = cli.invoke(app, ["rudderpin", "test"])
    assert result.exit_code == 5


def test_test_runs_all_suites_returns_first_failure(ws, calls):
    calls.codes.extend([3, 4])
    result = cli.invoke(app, ["test"])
    assert result.exit_code == 3
    assert [cmd for cmd, _ in calls] == [["uv", "run", "pytest"], ["npm", "test"]]


def test_test_runs_remaining_suite_when_a_directory_is_missing(ws, calls):
    (ws / "mantlepin/rudderpin").rmdir()
    result = cli.invoke(app, ["test"])
    assert result.exit_code == 2
    assert [cmd for cmd, _ in calls] == [["npm", "test"]]


def test_test_runs_remaining_suite_when_a_tool_is_missing(ws, calls, monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: None if name == "uv" else f"/usr/bin/{name}")
    result = cli.invoke(app, ["test"])
    assert result.exit_code == 127
    assert [cmd for cmd, _ in calls] == [["npm", "test"]]


def test_extra_args_pass_through(ws, calls):
    result = cli.invoke(app, ["rudderpin", "test", "-k", "ledger", "--maxfail=1"])
    assert result.exit_code == 0
    assert calls == [(["uv", "run", "pytest", "-k", "ledger", "--maxfail=1"], ws / "mantlepin/rudderpin")]
