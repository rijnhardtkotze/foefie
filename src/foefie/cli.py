"""Task runner for the ~/code workspace.

    mise run dev -- --help
    mise run dev -- rudderpin test
    uv run foefie concertforge build

Extra arguments after a command go to the underlying program, for example
`foefie rudderpin test -k ledger` runs `uv run pytest -k ledger`.
"""
from __future__ import annotations

from pathlib import Path

import typer

from foefie.runner import _run, run
from foefie.workspace import root

ROOT = root()
PASS_ARGS = {"allow_extra_args": True, "ignore_unknown_options": True}

RUDDERPIN = Path("mantlepin/rudderpin")
WEBSITE = Path("mantlepin/website")
CONCERTFORGE = Path("mantlepin-labs/concertforge")
REA_COMPANION = Path("mantlepin-labs/rea-remote/companion")
REA_INFRA = Path("mantlepin-labs/rea-remote/infra")


app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Task runner for ~/code. Pick a project, then a command.",
)


@app.command(help="Fast tests: rudderpin and the rea-remote companion.")
def test() -> None:
    # Run every suite so one failure does not hide the other; exit with the first failure.
    codes = [_run(RUDDERPIN, "uv", "run", "pytest"), _run(REA_COMPANION, "npm", "test")]
    code = next((c for c in codes if c), 0)
    if code:
        raise typer.Exit(code)


# ---- mantlepin/rudderpin (Python, uv) -------------------------------------

rudderpin = typer.Typer(no_args_is_help=True, help="mantlepin/rudderpin (Python, uv).")
app.add_typer(rudderpin, name="rudderpin")


@rudderpin.command(context_settings=PASS_ARGS, help="Install dependencies.")
def sync(ctx: typer.Context) -> None:
    run(RUDDERPIN, "uv", "sync", extra=ctx.args)


@rudderpin.command("test", context_settings=PASS_ARGS, help="pytest; no network.")
def rudderpin_test(ctx: typer.Context) -> None:
    run(RUDDERPIN, "uv", "run", "pytest", extra=ctx.args)


@rudderpin.command(context_settings=PASS_ARGS, help="Run the server on 127.0.0.1:3000.")
def serve(ctx: typer.Context) -> None:
    run(RUDDERPIN, "uv", "run", "server.py", extra=ctx.args)


@rudderpin.command(context_settings=PASS_ARGS, help="Check both calendars answer (read-only).")
def calendars(ctx: typer.Context) -> None:
    run(RUDDERPIN, "uv", "run", "scripts/check_calendars.py", extra=ctx.args)


@rudderpin.command(context_settings=PASS_ARGS, help="Four typed turns against live Deepgram (uses quota).")
def verify(ctx: typer.Context) -> None:
    run(RUDDERPIN, "uv", "run", "verify.py", extra=ctx.args)


# ---- mantlepin/website ----------------------------------------------------

website = typer.Typer(no_args_is_help=True, help="mantlepin/website.")
app.add_typer(website, name="website")


@website.command(context_settings=PASS_ARGS, help="Serve dist/ on port 4173 (--port N to change).")
def dev(ctx: typer.Context) -> None:
    run(WEBSITE, "node", "preview.mjs", extra=ctx.args)


# ---- mantlepin-labs/concertforge (bun, turbo) -----------------------------

concertforge = typer.Typer(no_args_is_help=True, help="mantlepin-labs/concertforge (bun, turbo).")
app.add_typer(concertforge, name="concertforge")


@concertforge.command("install", context_settings=PASS_ARGS, help="bun install.")
def cf_install(ctx: typer.Context) -> None:
    run(CONCERTFORGE, "bun", "install", extra=ctx.args)


@concertforge.command("dev", context_settings=PASS_ARGS, help="turbo dev.")
def cf_dev(ctx: typer.Context) -> None:
    run(CONCERTFORGE, "bun", "run", "dev", extra=ctx.args)


@concertforge.command("build", context_settings=PASS_ARGS, help="turbo build.")
def cf_build(ctx: typer.Context) -> None:
    run(CONCERTFORGE, "bun", "run", "build", extra=ctx.args)


@concertforge.command("check", context_settings=PASS_ARGS, help="ultracite check.")
def cf_check(ctx: typer.Context) -> None:
    run(CONCERTFORGE, "bun", "run", "check", extra=ctx.args)


@concertforge.command("fix", context_settings=PASS_ARGS, help="ultracite fix (edits files).")
def cf_fix(ctx: typer.Context) -> None:
    run(CONCERTFORGE, "bun", "run", "fix", extra=ctx.args)


@concertforge.command("test", context_settings=PASS_ARGS, help="turbo test.")
def cf_test(ctx: typer.Context) -> None:
    run(CONCERTFORGE, "bun", "run", "test", extra=ctx.args)


# ---- rea-remote -----------------------------------------------------------

rea = typer.Typer(no_args_is_help=True, help="rea-remote (companion service, infra).")
app.add_typer(rea, name="rea")


@rea.command("test", context_settings=PASS_ARGS, help="Companion unit tests.")
def rea_test(ctx: typer.Context) -> None:
    run(REA_COMPANION, "npm", "test", extra=ctx.args)


@rea.command(context_settings=PASS_ARGS, help="Routing and attack checks. Pass the caddy path: foefie rea e2e /path/to/caddy")
def e2e(ctx: typer.Context) -> None:
    run(REA_COMPANION, "npm", "run", "test:e2e", "--", extra=ctx.args)


@rea.command(context_settings=PASS_ARGS, help="tofu plan. Needs the provider tokens scripts/setup.sh exports. No apply here on purpose.")
def plan(ctx: typer.Context) -> None:
    run(REA_INFRA, "tofu", "plan", extra=ctx.args)


if __name__ == "__main__":
    app()
