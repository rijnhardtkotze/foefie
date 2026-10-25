import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from foefie import cli

README = """# ~/code

## alpha

| Project | GitHub | Description |
| --- | --- | --- |
| [aaa](alpha/aaa) | [alpha/aaa](https://github.com/alpha/aaa) | |
| [zzz](alpha/zzz) | [alpha/zzz](https://github.com/alpha/zzz) | |

## beta

| Project | GitHub | Description |
| --- | --- | --- |
| [one](beta/one) | [beta/one](https://github.com/beta/one) | |
"""


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folders = [{"name": "~/code", "path": "."}]
    for rel in ["alpha/aaa", "alpha/zzz", "beta/one"]:
        (tmp_path / rel).mkdir(parents=True)
        folders.append({"name": rel, "path": rel})
    (tmp_path / "dev.code-workspace").write_text(json.dumps({"folders": folders}, indent="\t") + "\n")
    (tmp_path / "README.md").write_text(README)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    # Defaults the wizard offers must not depend on the machine's git config.
    monkeypatch.setattr(cli, "_git_config", lambda key, cwd=None: {"user.email": "old@example.com"}.get(key, ""))
    return tmp_path


def paths(root: Path) -> list[str]:
    return [f["path"] for f in json.loads((root / "dev.code-workspace").read_text())["folders"]]


def local_git(project: Path, key: str) -> str:
    out = subprocess.run(["git", "config", "--local", key], cwd=project, capture_output=True, text=True)
    return out.stdout.strip()


def test_wizard_asks_and_registers_a_plain_project(root: Path) -> None:
    # org, name, description, type, author, email (accept default), no GitHub, go ahead
    answers = "1\nmid\nA middle project\nplain\nRijn\n\nn\ny\n"
    result = CliRunner().invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    assert "Python version" not in result.output
    project = root / "alpha/mid"
    assert (project / ".git").is_dir()
    assert (project / "README.md").read_text() == "# mid\n\nA middle project\n"
    assert "A middle project" in (project / "AGENTS.md").read_text()
    assert (project / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert local_git(project, "user.name") == "Rijn"
    # The accepted default already applies, so no local override is written.
    assert local_git(project, "user.email") == ""
    assert paths(root) == [".", "alpha/aaa", "alpha/mid", "alpha/zzz", "beta/one"]
    readme = (root / "README.md").read_text().splitlines()
    row = "| [mid](alpha/mid) | [alpha/mid](https://github.com/alpha/mid) | A middle project |"
    assert readme.index(row) == readme.index("| [aaa](alpha/aaa) | [alpha/aaa](https://github.com/alpha/aaa) | |") + 1


def test_options_skip_the_questions(root: Path) -> None:
    args = ["new", "beta/two", "-d", "", "-k", "plain", "--author", "", "--email", "", "--no-github"]
    result = CliRunner().invoke(cli.app, args, input="y\n")

    assert result.exit_code == 0, result.output
    assert "Project name" not in result.output
    assert "Author" not in result.output
    assert paths(root)[-1] == "beta/two"
    assert (root / "README.md").read_text().endswith("| [two](beta/two) | [beta/two](https://github.com/beta/two) |  |\n")


def test_wizard_reasks_for_a_taken_or_bad_name_and_type(root: Path) -> None:
    answers = "alpha\naaa\nbad name\nfresh\n\nweird\nplain\n\n\nn\nn\n"
    result = CliRunner().invoke(cli.app, ["new"], input=answers)

    assert "alpha/aaa already exists." in result.output
    assert "Use letters, digits" in result.output
    assert "Pick one of: app, package, lib, plain" in result.output
    # Declined at "Go ahead?", so nothing is written.
    assert result.exit_code == 1
    assert not (root / "alpha/fresh").exists()
    assert "alpha/fresh" not in paths(root)


def test_bad_options_are_refused(root: Path) -> None:
    for args, message in [
        (["new", "gamma/x"], "Unknown org 'gamma'"),
        (["new", "alpha/x", "-k", "nope"], "--kind must be one of"),
        (["new", "alpha/x", "--build-backend", "nope"], "--build-backend must be one of"),
    ]:
        result = CliRunner().invoke(cli.app, args)
        assert result.exit_code == 2
        assert message in result.output


def test_set_authors_skips_empty_fields(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\nrequires-python = ">=3.12"\n')

    cli.set_authors(pyproject, "", 'a"b@example.com')

    assert tomllib.loads(pyproject.read_text())["project"]["authors"] == [{"email": 'a"b@example.com'}]


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_lib_with_backend_and_author(root: Path) -> None:
    # org, name, description, type, Python (default), backend, author, email, no GitHub, go ahead
    answers = "beta\nkit\nA kit\nlib\n\nhatch\nRijn Kotze\nrijn@example.com\nn\ny\n"
    result = CliRunner().invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    project = root / "beta/kit"
    meta = tomllib.loads((project / "pyproject.toml").read_text())
    assert meta["project"]["authors"] == [{"name": "Rijn Kotze", "email": "rijn@example.com"}]
    assert meta["project"]["description"] == "A kit"
    assert meta["build-system"]["build-backend"] == "hatchling.build"
    assert (project / "src/kit/py.typed").exists()
    assert local_git(project, "user.email") == "rijn@example.com"
