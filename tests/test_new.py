import json
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
    return tmp_path


def paths(root: Path) -> list[str]:
    return [f["path"] for f in json.loads((root / "dev.code-workspace").read_text())["folders"]]


def test_wizard_asks_and_registers_a_plain_project(root: Path) -> None:
    # org 1 (alpha), name, description, plain, no GitHub, go ahead
    answers = "1\nmid\nA middle project\nn\nn\ny\n"
    result = CliRunner().invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    project = root / "alpha/mid"
    assert (project / ".git").is_dir()
    assert (project / "README.md").read_text() == "# mid\n\nA middle project\n"
    assert "A middle project" in (project / "AGENTS.md").read_text()
    assert (project / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert paths(root) == [".", "alpha/aaa", "alpha/mid", "alpha/zzz", "beta/one"]
    readme = (root / "README.md").read_text().splitlines()
    row = "| [mid](alpha/mid) | [alpha/mid](https://github.com/alpha/mid) | A middle project |"
    assert readme.index(row) == readme.index("| [aaa](alpha/aaa) | [alpha/aaa](https://github.com/alpha/aaa) | |") + 1


def test_options_skip_the_questions(root: Path) -> None:
    result = CliRunner().invoke(
        cli.app, ["new", "beta/two", "-d", "", "--plain", "--no-github"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    assert "Project name" not in result.output
    assert paths(root)[-1] == "beta/two"
    assert (root / "README.md").read_text().endswith("| [two](beta/two) | [beta/two](https://github.com/beta/two) |  |\n")


def test_wizard_reasks_for_a_taken_or_bad_name(root: Path) -> None:
    answers = "alpha\naaa\nbad name\nfresh\n\nn\nn\nn\n"
    result = CliRunner().invoke(cli.app, ["new"], input=answers)

    assert "alpha/aaa already exists." in result.output
    assert "Use letters, digits" in result.output
    # Declined at "Go ahead?", so nothing is written.
    assert result.exit_code == 1
    assert not (root / "alpha/fresh").exists()
    assert "alpha/fresh" not in paths(root)


def test_unknown_org_is_refused(root: Path) -> None:
    result = CliRunner().invoke(cli.app, ["new", "gamma/x"])

    assert result.exit_code == 2
    assert "Unknown org 'gamma'" in result.output
