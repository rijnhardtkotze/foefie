import json
import subprocess
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from foefie import cli, config, new, runner

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
    monkeypatch.setattr(new, "root", lambda: tmp_path)
    monkeypatch.setattr(runner, "root", lambda: tmp_path)
    # The wizard must write the temp workspace's config, never the user's or the bundled example.
    monkeypatch.delenv("FOEFIE_CONFIG", raising=False)
    # Defaults the wizard offers must not depend on the machine's git config.
    monkeypatch.setattr(new, "_git_config", lambda key, cwd=None: {"user.email": "old@example.com"}.get(key, ""))
    return tmp_path


@pytest.fixture
def uv_init(root: Path, monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Stand in for `uv init` (and `gh`): record the call and make the directory uv would have made."""
    made: list[tuple] = []
    real = new.run

    def fake_run(where: Path, *cmd: str, extra: list[str] | None = None) -> None:
        if cmd[:2] != ("uv", "init"):
            return real(where, *cmd, extra=extra)
        made.append((where, cmd))
        project = root / where / cmd[-1]
        project.mkdir(parents=True)
        (project / "pyproject.toml").write_text(f'[project]\nname = "{cmd[-1]}"\nrequires-python = ">=3.12"\n')
        # uv init --vcs git makes a repo; the wizard then sets git config inside it.
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

    monkeypatch.setattr(new, "run", fake_run)
    return made


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
    row = "| [two](beta/two) | [beta/two](https://github.com/beta/two) |  |\n"
    assert (root / "README.md").read_text().endswith(row)


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
    assert not (root / "foefie.toml").exists()


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

    new.set_authors(pyproject, "", 'a"b@example.com')

    assert tomllib.loads(pyproject.read_text())["project"]["authors"] == [{"email": 'a"b@example.com'}]


def test_lib_with_backend_and_author(root: Path, uv_init: list[tuple]) -> None:
    # org, name, description, type, Python (default), backend, author, email, no GitHub, go ahead
    answers = "beta\nkit\nA kit\nlib\n\nhatch\nRijn Kotze\nrijn@example.com\nn\ny\n"
    result = CliRunner().invoke(cli.app, ["new"], input=answers)

    assert result.exit_code == 0, result.output
    [(where, cmd)] = uv_init
    assert where == Path("beta")
    assert cmd == (
        "uv", "init", "--lib", "--vcs", "git", "--no-workspace", "--author-from", "none",
        "--description", "A kit", "--build-backend", "hatch", "kit",
    )  # fmt: skip
    project = root / "beta/kit"
    meta = tomllib.loads((project / "pyproject.toml").read_text())
    assert meta["project"]["authors"] == [{"name": "Rijn Kotze", "email": "rijn@example.com"}]
    assert (project / "AGENTS.md").is_file()
    assert local_git(project, "user.email") == "rijn@example.com"


def plain(target: str, description: str = "") -> list[str]:
    return ["new", target, "-d", description, "-k", "plain", "--author", "", "--email", "", "--no-github"]


def test_project_is_appended_to_foefie_toml(root: Path) -> None:
    result = CliRunner().invoke(cli.app, plain("beta/two", "Two"), input="y\n")

    assert result.exit_code == 0, result.output
    # No foefie.toml yet, so it starts from the bundled example; the example itself stays untouched.
    text = (root / "foefie.toml").read_text()
    assert text.startswith(config.EXAMPLE.read_text())
    assert "beta/two" not in config.EXAMPLE.read_text()
    cfg = config.load_config(root / "foefie.toml")
    assert cfg.projects["two"] == config.Project("two", Path("beta/two"), "Two")
    assert "rudderpin" in cfg.projects


def test_existing_foefie_toml_entries_are_kept(root: Path) -> None:
    own = (
        "# mine\n"
        '[[projects]]\nname = "two"\npath = "elsewhere/two"\n\n'
        '[[projects]]\nname = "other"\npath = "beta/one"\n'
    )
    (root / "foefie.toml").write_text(own)
    result = CliRunner().invoke(cli.app, plain("beta/two"), input="y\n")

    # A project already named "two" is never replaced; the wizard says so and still creates the folder.
    assert result.exit_code == 0, result.output
    assert "foefie.toml" in result.output
    assert (root / "foefie.toml").read_text() == own
    assert (root / "beta/two").is_dir()

    assert CliRunner().invoke(cli.app, plain("beta/three"), input="y\n").exit_code == 0
    text = (root / "foefie.toml").read_text()
    assert text.startswith(own)
    assert list(config.load_config(root / "foefie.toml").projects) == ["two", "other", "three"]
