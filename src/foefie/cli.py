"""Task runner for the ~/code workspace.

    mise run dev -- --help
    mise run dev -- rudderpin test
    mise run dev -- new             a wizard that starts a new project
    uv run foefie concertforge build

Projects and commands come from foefie.toml (see foefie.example.toml). Extra
arguments after a command go to the underlying program, for example
`foefie rudderpin test -k ledger` runs `uv run pytest -k ledger`.
"""
from __future__ import annotations

import typer

from foefie.config import Command, Config, ConfigError, load_config
from foefie.new import new_project
from foefie.runner import _run, run

PASS_ARGS = {"allow_extra_args": True, "ignore_unknown_options": True}


def _command(cfg: Config, command: Command):
    where = cfg.workdir(command)

    def callback(ctx: typer.Context) -> None:
        run(where, *command.argv, extra=ctx.args)

    return callback


def _steps(cfg: Config, command: Command):
    steps = [cfg.command(project, name) for project, name in command.steps]

    def callback() -> None:
        # Run every step so one failure does not hide the others; exit with the first failure.
        codes = [_run(cfg.workdir(step), *step.argv) for step in steps]
        code = next((c for c in codes if c), 0)
        if code:
            raise typer.Exit(code)

    return callback


def build_app(cfg: Config) -> typer.Typer:
    app = typer.Typer(
        no_args_is_help=True,
        add_completion=False,
        help="Task runner for ~/code. Pick a project, then a command.",
    )
    groups = {
        name: typer.Typer(no_args_is_help=True, help=project.help or None) for name, project in cfg.projects.items()
    }
    for command in cfg.commands:
        if command.project is None:
            app.command(command.name, help=command.help or None)(_steps(cfg, command))
        else:
            groups[command.project].command(
                command.name,
                context_settings=PASS_ARGS if command.passthrough else None,
                help=command.help or None,
            )(_command(cfg, command))
    app.command("new", help="Start a new project. Asks for anything not given as an option.")(new_project)
    for name, group in groups.items():
        app.add_typer(group, name=name)
    return app


try:
    app = build_app(load_config())
except ConfigError as err:
    raise SystemExit(str(err)) from None


if __name__ == "__main__":
    app()
