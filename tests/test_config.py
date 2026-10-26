import pytest
from typer.testing import CliRunner

from foefie import config, runner
from foefie.cli import build_app
from foefie.config import ConfigError, load_config

cli = CliRunner()

DEMO = """
[[projects]]
name = "demo"
path = "apps/demo"
help = "The demo app."

[[commands]]
name = "hello"
project = "demo"
argv = ["echo", "hi"]
help = "Say hi."

[[commands]]
name = "strict"
project = "demo"
argv = ["true"]
passthrough = false

[[commands]]
name = "sub"
project = "demo"
argv = ["make"]
cwd = "nested"

[[commands]]
name = "all"
steps = ["demo hello", "demo sub"]
help = "Run everything."
"""

# The 16 commands foefie 0.1 shipped with: "project command" -> (directory, argv).
V0_COMMANDS = {
    "rudderpin sync": ("mantlepin/rudderpin", ("uv", "sync")),
    "rudderpin test": ("mantlepin/rudderpin", ("uv", "run", "pytest")),
    "rudderpin serve": ("mantlepin/rudderpin", ("uv", "run", "server.py")),
    "rudderpin calendars": ("mantlepin/rudderpin", ("uv", "run", "scripts/check_calendars.py")),
    "rudderpin verify": ("mantlepin/rudderpin", ("uv", "run", "verify.py")),
    "website dev": ("mantlepin/website", ("node", "preview.mjs")),
    "concertforge install": ("mantlepin-labs/concertforge", ("bun", "install")),
    "concertforge dev": ("mantlepin-labs/concertforge", ("bun", "run", "dev")),
    "concertforge build": ("mantlepin-labs/concertforge", ("bun", "run", "build")),
    "concertforge check": ("mantlepin-labs/concertforge", ("bun", "run", "check")),
    "concertforge fix": ("mantlepin-labs/concertforge", ("bun", "run", "fix")),
    "concertforge test": ("mantlepin-labs/concertforge", ("bun", "run", "test")),
    "rea test": ("mantlepin-labs/rea-remote/companion", ("npm", "test")),
    "rea e2e": ("mantlepin-labs/rea-remote/companion", ("npm", "run", "test:e2e", "--")),
    "rea plan": ("mantlepin-labs/rea-remote/infra", ("tofu", "plan")),
    "test": (None, None),
}


def write(tmp_path, text, name="foefie.toml"):
    path = tmp_path / name
    path.write_text(text)
    return path


@pytest.fixture
def demo_ws(tmp_path, monkeypatch):
    (tmp_path / "apps/demo/nested").mkdir(parents=True)
    monkeypatch.setattr(runner, "root", lambda: tmp_path)
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/bin/{name}")
    return tmp_path


def test_config_builds_subcommands(demo_ws, calls):
    app = build_app(load_config(write(demo_ws, DEMO)))

    result = cli.invoke(app, ["demo", "hello", "--loud"])
    assert result.exit_code == 0
    assert calls == [(["echo", "hi", "--loud"], demo_ws / "apps/demo")]

    calls.clear()
    result = cli.invoke(app, ["all"])
    assert result.exit_code == 0
    assert calls == [(["echo", "hi"], demo_ws / "apps/demo"), (["make"], demo_ws / "apps/demo/nested")]

    help_out = cli.invoke(app, ["--help"]).output
    assert "demo" in help_out
    assert "Run everything." in help_out
    assert "Say hi." in cli.invoke(app, ["demo", "--help"]).output


def test_config_passthrough_false_rejects_extra_args(demo_ws, calls):
    app = build_app(load_config(write(demo_ws, DEMO)))
    result = cli.invoke(app, ["demo", "strict", "extra"])
    assert result.exit_code == 2
    assert calls == []


def test_config_steps_run_every_step_and_return_first_failure(demo_ws, calls):
    app = build_app(load_config(write(demo_ws, DEMO)))
    calls.codes.extend([3, 4])
    result = cli.invoke(app, ["all"])
    assert result.exit_code == 3
    assert [cmd for cmd, _ in calls] == [["echo", "hi"], ["make"]]


BAD = {
    "unknown project": ('[[commands]]\nname = "x"\nproject = "nope"\nargv = ["true"]\n', "commands[0].project"),
    "empty argv": (
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nname = "x"\nproject = "p"\nargv = []\n',
        "commands[0].argv",
    ),
    "argv not strings": (
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nname = "x"\nproject = "p"\nargv = ["a", 1]\n',
        "commands[0].argv[1]",
    ),
    "missing name": (
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nproject = "p"\nargv = ["true"]\n',
        "commands[0].name",
    ),
    "unknown key": ('[[projects]]\nname = "p"\npath = "p"\ncolour = "red"\n', "projects[0].colour"),
    "absolute path": ('[[projects]]\nname = "p"\npath = "/etc"\n', "projects[0].path"),
    "duplicate project": (
        '[[projects]]\nname = "p"\npath = "a"\n[[projects]]\nname = "p"\npath = "b"\n',
        "projects[1].name",
    ),
    "duplicate command": (
        '[[projects]]\nname = "p"\npath = "p"\n'
        '[[commands]]\nname = "x"\nproject = "p"\nargv = ["a"]\n'
        '[[commands]]\nname = "x"\nproject = "p"\nargv = ["b"]\n',
        "commands[1].name",
    ),
    "unknown step": ('[[commands]]\nname = "all"\nsteps = ["p x"]\n', "commands[0].steps[0]"),
    "argv and steps": (
        '[[projects]]\nname = "p"\npath = "p"\n'
        '[[commands]]\nname = "x"\nproject = "p"\nargv = ["a"]\nsteps = ["p x"]\n',
        "commands[0].steps",
    ),
    "cwd escapes project": (
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nname = "x"\nproject = "p"\nargv = ["a"]\ncwd = "../x"\n',
        "commands[0].cwd",
    ),
    "command named like a project": (
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nname = "p"\nsteps = []\n',
        "commands[0].name",
    ),
    "top-level command named new": (
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nname = "new"\nsteps = ["p x"]\n',
        "commands[0].name",
    ),
    "project named new": ('[[projects]]\nname = "new"\npath = "p"\n', "projects[0].name"),
}


@pytest.mark.parametrize(("text", "key"), BAD.values(), ids=BAD.keys())
def test_config_invalid_reports_key(tmp_path, text, key):
    path = write(tmp_path, text)
    with pytest.raises(ConfigError) as err:
        load_config(path)
    message = str(err.value)
    assert str(path) in message
    assert key in message


def test_config_allows_new_inside_a_project(tmp_path):
    # `foefie p new` does not collide with the built-in `foefie new`.
    path = write(
        tmp_path,
        '[[projects]]\nname = "p"\npath = "p"\n[[commands]]\nname = "new"\nproject = "p"\nargv = ["a"]\n',
    )
    assert load_config(path).command("p", "new").argv == ("a",)


def test_config_invalid_toml_reports_file(tmp_path):
    path = write(tmp_path, "this is = = not toml")
    with pytest.raises(ConfigError, match=str(path)):
        load_config(path)


def test_example_config_matches_v0_commands():
    cfg = load_config(config.EXAMPLE)
    assert len(V0_COMMANDS) == 16
    found = {}
    for command in cfg.commands:
        if command.project is None:
            found[command.name] = (None, None)
        else:
            found[f"{command.project} {command.name}"] = (str(cfg.workdir(command)), command.argv)
    assert found == V0_COMMANDS
    assert next(c for c in cfg.commands if c.name == "test" and c.project is None).steps == (
        ("rudderpin", "test"),
        ("rea", "test"),
    )
    assert [p.name for p in cfg.projects.values()] == ["rudderpin", "website", "concertforge", "rea"]


def test_config_env_override(tmp_path, monkeypatch):
    path = write(tmp_path, DEMO, name="elsewhere.toml")
    monkeypatch.setenv("FOEFIE_CONFIG", str(path))
    assert config.config_path() == path
    assert list(load_config().projects) == ["demo"]


def test_config_env_override_missing_file_names_it(tmp_path, monkeypatch):
    missing = tmp_path / "nope.toml"
    monkeypatch.setenv("FOEFIE_CONFIG", str(missing))
    with pytest.raises(ConfigError, match=str(missing)):
        load_config()


def test_config_defaults_to_workspace_file_then_example(tmp_path, monkeypatch):
    monkeypatch.delenv("FOEFIE_CONFIG", raising=False)
    monkeypatch.setattr(config, "root", lambda: tmp_path)
    assert config.config_path() == config.EXAMPLE
    own = write(tmp_path, DEMO)
    assert config.config_path() == own
