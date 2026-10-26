"""The foefie.toml schema: projects and the commands run inside them."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePath

from foefie.workspace import root

CONFIG_NAME = "foefie.toml"
ENV_VAR = "FOEFIE_CONFIG"
EXAMPLE = Path(__file__).with_name("foefie.example.toml")

# Top-level names the CLI defines itself; a project or top-level command cannot use them.
RESERVED = frozenset({"new"})

PROJECT_KEYS = {"name", "path", "help"}
COMMAND_KEYS = {"name", "project", "argv", "cwd", "help", "passthrough", "steps"}


class ConfigError(Exception):
    """An invalid config; the message names the file and the offending key."""


@dataclass(frozen=True)
class Project:
    name: str
    path: Path
    help: str = ""


@dataclass(frozen=True)
class Command:
    name: str
    project: str | None = None
    argv: tuple[str, ...] = ()
    cwd: Path | None = None
    help: str = ""
    passthrough: bool = True
    steps: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Config:
    source: Path
    projects: dict[str, Project]
    commands: tuple[Command, ...]

    def command(self, project: str | None, name: str) -> Command:
        return next(c for c in self.commands if c.project == project and c.name == name)

    def workdir(self, command: Command) -> Path:
        """The directory a command runs in, relative to the workspace root."""
        base = self.projects[command.project].path
        return base / command.cwd if command.cwd else base


def config_path() -> Path:
    """FOEFIE_CONFIG if set, else foefie.toml in the workspace root, else the bundled example."""
    if env := os.environ.get(ENV_VAR):
        return Path(env).expanduser()
    own = root() / CONFIG_NAME
    return own if own.is_file() else EXAMPLE


def write_path(base: Path) -> Path:
    """The file `foefie new` adds projects to: FOEFIE_CONFIG if set, else foefie.toml in the root.

    Never the bundled example, which is read-only reference.
    """
    if env := os.environ.get(ENV_VAR):
        path = Path(env).expanduser()
        if path.resolve() != EXAMPLE.resolve():
            return path
    return base / CONFIG_NAME


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        raise ConfigError(f"{path}: config file not found") from None
    except (OSError, UnicodeDecodeError) as err:
        raise ConfigError(f"{path}: cannot read config ({err})") from None
    except tomllib.TOMLDecodeError as err:
        raise ConfigError(f"{path}: invalid TOML ({err})") from None
    return _parse(path, data)


def _parse(path: Path, data: dict) -> Config:
    def fail(key: str, problem: str) -> ConfigError:
        return ConfigError(f"{path}: {key}: {problem}")

    for key in data:
        if key not in ("projects", "commands"):
            raise fail(key, "unknown key (expected projects or commands)")

    projects: dict[str, Project] = {}
    for i, raw in enumerate(_tables(data.get("projects", []), "projects", fail)):
        at = f"projects[{i}]"
        _only(raw, PROJECT_KEYS, at, fail)
        name = _text(raw, "name", at, fail)
        if name in RESERVED:
            raise fail(f"{at}.name", f"{name!r} is a built-in command and cannot be a project")
        if name in projects:
            raise fail(f"{at}.name", f"duplicate project {name!r}")
        projects[name] = Project(name, _relative(raw, "path", at, fail), _text(raw, "help", at, fail, ""))

    commands: list[Command] = []
    for i, raw in enumerate(_tables(data.get("commands", []), "commands", fail)):
        at = f"commands[{i}]"
        _only(raw, COMMAND_KEYS, at, fail)
        name = _text(raw, "name", at, fail)
        project = raw.get("project")
        if project is not None and project not in projects:
            raise fail(f"{at}.project", f"unknown project {project!r}")
        if project is None and name in RESERVED:
            raise fail(f"{at}.name", f"{name!r} is a built-in command and cannot be redefined")
        if project is None and name in projects:
            raise fail(f"{at}.name", f"{name!r} is already a project")
        if any(c.project == project and c.name == name for c in commands):
            raise fail(f"{at}.name", f"duplicate command {name!r}")
        help_text = _text(raw, "help", at, fail, "")

        if project is None:
            for key in ("argv", "cwd", "passthrough"):
                if key in raw:
                    raise fail(f"{at}.{key}", "only valid on a command with a project")
            steps = _steps(raw, at, fail)
            commands.append(Command(name, help=help_text, steps=steps, passthrough=False))
            continue

        if "steps" in raw:
            raise fail(f"{at}.steps", "only valid on a command without a project")
        argv = _strings(raw, "argv", at, fail)
        cwd = _relative(raw, "cwd", at, fail) if "cwd" in raw else None
        passthrough = raw.get("passthrough", True)
        if not isinstance(passthrough, bool):
            raise fail(f"{at}.passthrough", "must be true or false")
        commands.append(Command(name, project, tuple(argv), cwd, help_text, passthrough))

    for i, command in enumerate(commands):
        for j, (project, name) in enumerate(command.steps):
            if not any(c.project == project and c.name == name and c.argv for c in commands):
                raise fail(f"commands[{i}].steps[{j}]", f"no command {project} {name}")

    return Config(path, projects, tuple(commands))


def _tables(value, key, fail):
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise fail(key, "must be an array of tables")
    return value


def _only(raw, allowed, at, fail):
    for key in raw:
        if key not in allowed:
            raise fail(f"{at}.{key}", f"unknown key (allowed: {', '.join(sorted(allowed))})")


def _text(raw, key, at, fail, default=None):
    if key not in raw:
        if default is None:
            raise fail(f"{at}.{key}", "required")
        return default
    value = raw[key]
    if not isinstance(value, str) or (default is None and not value.strip()):
        raise fail(f"{at}.{key}", "must be a non-empty string" if default is None else "must be a string")
    return value


def _relative(raw, key, at, fail) -> Path:
    value = Path(_text(raw, key, at, fail))
    if value.is_absolute() or ".." in PurePath(value).parts:
        raise fail(f"{at}.{key}", "must be a relative path without '..'")
    return value


def _strings(raw, key, at, fail) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise fail(f"{at}.{key}", "must be a non-empty array of strings")
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise fail(f"{at}.{key}[{i}]", "must be a non-empty string")
    return value


def _steps(raw, at, fail) -> tuple[tuple[str, str], ...]:
    items = raw.get("steps")
    if not isinstance(items, list) or not items:
        raise fail(f"{at}.steps", "required: a non-empty array of 'project command' strings")
    steps = []
    for i, item in enumerate(items):
        parts = item.split() if isinstance(item, str) else []
        if len(parts) != 2:
            raise fail(f"{at}.steps[{i}]", "must be a string like 'project command'")
        steps.append((parts[0], parts[1]))
    return tuple(steps)
