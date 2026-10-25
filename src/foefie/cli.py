"""Task runner for the ~/code workspace.

    mise run dev -- --help
    mise run dev -- rudderpin test
    mise run dev -- new             a wizard that starts a new project
    uv run foefie concertforge build

Extra arguments after a command go to the underlying program, for example
`foefie rudderpin test -k ledger` runs `uv run pytest -k ledger`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import typer

def _find_root() -> Path:
    """The workspace root: the nearest parent holding dev.code-workspace.

    Search up from the current directory first, so a non-editable install still
    finds the workspace it is run from. Fall back to this file's location.
    """
    start = Path.cwd().resolve()
    for parent in [start, *start.parents, *Path(__file__).resolve().parents]:
        if (parent / "dev.code-workspace").is_file():
            return parent
    raise SystemExit(f"dev.code-workspace not found above {start} or {Path(__file__)}")


ROOT = _find_root()
PASS_ARGS = {"allow_extra_args": True, "ignore_unknown_options": True}

RUDDERPIN = Path("mantlepin/rudderpin")
WEBSITE = Path("mantlepin/website")
CONCERTFORGE = Path("mantlepin-labs/concertforge")
REA_COMPANION = Path("mantlepin-labs/rea-remote/companion")
REA_INFRA = Path("mantlepin-labs/rea-remote/infra")


def _run(where: Path, *cmd: str, extra: list[str] | None = None) -> int:
    """Run a command in a project directory and return its exit status."""
    full = [*cmd, *(extra or [])]
    cwd = ROOT / where
    if not cwd.is_dir():
        typer.secho(f"{where} does not exist", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    if shutil.which(full[0]) is None:
        typer.secho(
            f"{full[0]} not found on PATH. Run `mise install` in {ROOT}.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(127)
    typer.secho(f"[{where}] $ {' '.join(full)}", dim=True)
    return subprocess.run(full, cwd=cwd).returncode


def run(where: Path, *cmd: str, extra: list[str] | None = None) -> None:
    """Run a command in a project directory and exit with its status if it fails."""
    code = _run(where, *cmd, extra=extra)
    if code:
        raise typer.Exit(code)


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


# ---- new project ----------------------------------------------------------

NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

AGENTS_MD = """# {name}

{description}

## Rules

- Tool versions come from `mise.toml` in ~/code; add a project `mise.toml` only to pin something different.
- Workspace rules are in ~/code/AGENTS.md.
"""


def workspace_orgs(root: Path) -> list[str]:
    """Org folders, in the order dev.code-workspace lists them."""
    folders = json.loads((root / "dev.code-workspace").read_text())["folders"]
    orgs = [f["path"].split("/")[0] for f in folders if "/" in f.get("path", "")]
    return list(dict.fromkeys(orgs))


def add_to_workspace(root: Path, rel: str) -> bool:
    """List a folder in dev.code-workspace. Return False if it is already there."""
    path = root / "dev.code-workspace"
    data = json.loads(path.read_text())
    folders = data["folders"]
    if any(f.get("path") == rel for f in folders):
        return False
    org = rel.split("/")[0] + "/"
    same = [i for i, f in enumerate(folders) if f.get("path", "").startswith(org)]
    # Keep each org's folders in name order; a new org goes last.
    at = next((i for i in same if folders[i]["path"] > rel), same[-1] + 1 if same else len(folders))
    folders.insert(at, {"name": rel, "path": rel})
    path.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n")
    return True


def add_to_readme(root: Path, org: str, name: str, description: str) -> bool:
    """Add a row to the README table under `## <org>`, in name order.

    Return False when there is no such table or the project is already in it.
    """
    path = root / "README.md"
    lines = path.read_text().splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip() == f"## {org}"), None)
    if start is None:
        return False
    i = start + 1
    while i < len(lines) and not lines[i].startswith("| ---"):
        if lines[i].startswith("## "):
            return False
        i += 1
    i += 1
    row = f"| [{name}]({org}/{name}) | [{org}/{name}](https://github.com/{org}/{name}) | {description} |\n"
    while i < len(lines) and lines[i].startswith("|"):
        if lines[i].startswith(f"| [{name}]("):
            return False
        if lines[i].lower() > row.lower():
            break
        i += 1
    lines.insert(i, row)
    path.write_text("".join(lines))
    return True


def _ask_org(orgs: list[str]) -> str:
    for n, org in enumerate(orgs, 1):
        typer.echo(f"  {n}. {org}")
    while True:
        answer = typer.prompt("Org (number or name)", default="1").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(orgs):
            return orgs[int(answer) - 1]
        if answer in orgs:
            return answer
        typer.secho(f"Pick 1-{len(orgs)} or one of: {', '.join(orgs)}", fg=typer.colors.RED)


def _ask_name(org: str) -> str:
    while True:
        name = typer.prompt("Project name").strip()
        if not NAME_RE.fullmatch(name):
            typer.secho("Use letters, digits, '.', '_' or '-'.", fg=typer.colors.RED)
        elif (ROOT / org / name).exists():
            typer.secho(f"{org}/{name} already exists.", fg=typer.colors.RED)
        else:
            return name


def _fail(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(2)


# Project types and the uv init flags behind them. "package" is an app with a
# build system and a console script; "plain" skips uv.
KINDS = {
    "app": ["--app"],
    "package": ["--app", "--package"],
    "lib": ["--lib"],
    "plain": [],
}
BACKENDS = ["uv", "hatch", "flit", "pdm", "poetry", "setuptools", "maturin", "scikit"]


def _git_config(key: str, cwd: Path | None = None) -> str:
    out = subprocess.run(["git", "config", key], capture_output=True, text=True, cwd=cwd)
    return out.stdout.strip()


def _ask_choice(label: str, choices: list[str], default: str) -> str:
    while True:
        answer = typer.prompt(f"{label} ({'/'.join(choices)})", default=default).strip()
        if answer in choices:
            return answer
        typer.secho(f"Pick one of: {', '.join(choices)}", fg=typer.colors.RED)


def set_authors(pyproject: Path, name: str, email: str) -> None:
    """Write an authors entry above requires-python; uv init was told to leave it out."""
    fields = ", ".join(f"{k} = {json.dumps(v)}" for k, v in (("name", name), ("email", email)) if v)
    if not fields:
        return
    text = pyproject.read_text()
    text = text.replace("requires-python", f"authors = [\n    {{ {fields} }}\n]\nrequires-python", 1)
    pyproject.write_text(text)


@app.command(help="Start a new project. Asks for anything not given as an option.")
def new(
    target: str = typer.Argument("", metavar="[ORG/NAME]", help="Skip the org and name questions."),
    description: str = typer.Option(None, "--description", "-d", help="One line for the README and AGENTS.md."),
    kind: str = typer.Option(None, "--kind", "-k", help="app, package (app with a build system), lib, or plain (git only)."),
    python: str = typer.Option(None, "--python", "-p", help="Python version for uv init; empty for uv's default."),
    backend: str = typer.Option(None, "--build-backend", help=f"For package and lib: {', '.join(BACKENDS)}."),
    author: str = typer.Option(None, "--author", help="Author name; defaults to git config user.name."),
    email: str = typer.Option(None, "--email", help="Author email; defaults to git config user.email."),
    github: bool = typer.Option(None, "--github/--no-github", help="Create a private GitHub repo (no push)."),
) -> None:
    if kind is not None and kind not in KINDS:
        _fail(f"--kind must be one of: {', '.join(KINDS)}")
    if backend is not None and backend not in BACKENDS:
        _fail(f"--build-backend must be one of: {', '.join(BACKENDS)}")
    orgs = workspace_orgs(ROOT)
    if target:
        org, _, name = target.partition("/")
        if org not in orgs:
            _fail(f"Unknown org {org!r}. Known: {', '.join(orgs)}")
        if not NAME_RE.fullmatch(name):
            _fail("Give the project as <org>/<name>, e.g. rijnhardtkotze/tidy")
        if (ROOT / org / name).exists():
            _fail(f"{org}/{name} already exists.")
    else:
        org = _ask_org(orgs)
        name = _ask_name(org)
    if description is None:
        description = typer.prompt("One-line description", default="", show_default=False).strip()
    if kind is None:
        typer.echo("Types: app (script), package (app you can install), lib (library), plain (git only)")
        kind = _ask_choice("Type", list(KINDS), "package")
    if kind != "plain":
        if python is None:
            python = typer.prompt("Python version (empty for uv's default)", default="", show_default=False).strip()
        if kind in ("package", "lib") and backend is None:
            backend = _ask_choice("Build backend", BACKENDS, "uv")
    if author is None:
        default = _git_config("user.name")
        author = typer.prompt("Author name", default=default, show_default=bool(default)).strip()
    if email is None:
        default = _git_config("user.email")
        email = typer.prompt("Author email", default=default, show_default=bool(default)).strip()
    if github is None:
        github = typer.confirm(f"Create private GitHub repo {org}/{name}?", default=False)

    rel = Path(org, name)
    summary = [kind]
    if kind != "plain":
        summary.append(f"Python {python or 'default'}")
    if backend and kind in ("package", "lib"):
        summary.append(f"{backend} backend")
    summary.append(f"author {author or '-'} <{email or '-'}>")
    if github:
        summary.append("GitHub")
    typer.echo(f"\nCreating {rel}: {', '.join(summary)}")
    if not typer.confirm("Go ahead?", default=True):
        raise typer.Abort()

    if kind != "plain":
        flags = [*KINDS[kind], "--vcs", "git", "--no-workspace", "--author-from", "none"]
        if description:
            flags += ["--description", description]
        if python:
            flags += ["--python", python]
        if backend and kind in ("package", "lib"):
            flags += ["--build-backend", backend]
        run(Path(org), "uv", "init", *flags, name)
        set_authors(ROOT / rel / "pyproject.toml", author, email)
    else:
        (ROOT / rel).mkdir(parents=True)
        run(rel, "git", "init", "-q")
        (ROOT / rel / "README.md").write_text(f"# {name}\n" + (f"\n{description}\n" if description else ""))
    (ROOT / rel / "AGENTS.md").write_text(AGENTS_MD.format(name=name, description=description or "TODO: what this is."))
    (ROOT / rel / "CLAUDE.md").write_text("@AGENTS.md\n")
    # Commits in this repo carry the author given above, whatever the global git config says.
    for key, value in (("user.name", author), ("user.email", email)):
        if value and value != _git_config(key, ROOT / rel):
            subprocess.run(["git", "config", key, value], cwd=ROOT / rel, check=True)

    if not add_to_workspace(ROOT, rel.as_posix()):
        typer.secho("dev.code-workspace already lists it.", dim=True)
    if not add_to_readme(ROOT, org, name, description):
        typer.secho(f"README.md: no `## {org}` table or row already there; add it by hand.", fg=typer.colors.YELLOW)
    if github:
        desc = ["--description", description] if description else []
        run(rel, "gh", "repo", "create", f"{org}/{name}", "--private", "--source", ".", "--remote", "origin", *desc)

    typer.secho(f"\nCreated {rel}.", fg=typer.colors.GREEN)
    typer.echo(f"  goto {name}")
    typer.echo('  git add -A && git commit -m "Initial commit"')


if __name__ == "__main__":
    app()
