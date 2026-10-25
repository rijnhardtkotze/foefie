"""The `foefie new` wizard: start a project and register it in the workspace."""
from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

import typer

from foefie.config import EXAMPLE, write_path
from foefie.runner import run
from foefie.workspace import root

NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

AGENTS_MD = """# {name}

{description}

## Rules

- Tool versions come from `mise.toml` in ~/code; add a project `mise.toml` only to pin something different.
- Workspace rules are in ~/code/AGENTS.md.
"""

# Project types and the uv init flags behind them. "package" is an app with a
# build system and a console script; "plain" skips uv.
KINDS = {
    "app": ["--app"],
    "package": ["--app", "--package"],
    "lib": ["--lib"],
    "plain": [],
}
BACKENDS = ["uv", "hatch", "flit", "pdm", "poetry", "setuptools", "maturin", "scikit"]


def workspace_orgs(base: Path) -> list[str]:
    """Org folders, in the order dev.code-workspace lists them."""
    folders = json.loads((base / "dev.code-workspace").read_text())["folders"]
    orgs = [f["path"].split("/")[0] for f in folders if "/" in f.get("path", "")]
    return list(dict.fromkeys(orgs))


def add_to_workspace(base: Path, rel: str) -> bool:
    """List a folder in dev.code-workspace. Return False if it is already there."""
    path = base / "dev.code-workspace"
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


def add_to_readme(base: Path, org: str, name: str, description: str) -> bool:
    """Add a row to the README table under `## <org>`, in name order.

    Return False when there is no such table or the project is already in it.
    """
    path = base / "README.md"
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


def add_to_config(path: Path, name: str, rel: str, description: str) -> bool:
    """Append a project to foefie.toml, starting from the bundled example if the file is missing.

    Existing text is never rewritten. Return False, leaving the file as it is, when the name is taken
    or the file is not valid TOML.
    """
    text = path.read_text() if path.exists() else EXAMPLE.read_text()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False
    taken = {p.get("name") for p in data.get("projects", [])}
    taken |= {c.get("name") for c in data.get("commands", []) if "project" not in c}
    if name in taken or name == "new":
        return False
    entry = "[[projects]]\n" + "".join(
        f"{key} = {json.dumps(value)}\n" for key, value in (("name", name), ("path", rel), ("help", description or rel))
    )
    text =text + ("" if text.endswith("\n") else "\n") + ("\n" if text.strip() else "") + entry
    path.write_text(text)
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


def _ask_name(base: Path, org: str) -> str:
    while True:
        name = typer.prompt("Project name").strip()
        if not NAME_RE.fullmatch(name):
            typer.secho("Use letters, digits, '.', '_' or '-'.", fg=typer.colors.RED)
        elif (base / org / name).exists():
            typer.secho(f"{org}/{name} already exists.", fg=typer.colors.RED)
        else:
            return name


def _fail(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(2)


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


def new_project(
    target: str = typer.Argument("", metavar="[ORG/NAME]", help="Skip the org and name questions."),
    description: str = typer.Option(None, "--description", "-d", help="One line for the README and AGENTS.md."),
    kind: str = typer.Option(
        None, "--kind", "-k", help="app, package (app with a build system), lib, or plain (git only)."
    ),
    python: str = typer.Option(None, "--python", "-p", help="Python version for uv init; empty for uv's default."),
    backend: str = typer.Option(
        None, "--build-backend", help=f"For package and lib: {', '.join(BACKENDS)}."
    ),
    author: str = typer.Option(None, "--author", help="Author name; defaults to git config user.name."),
    email: str = typer.Option(None, "--email", help="Author email; defaults to git config user.email."),
    github: bool = typer.Option(None, "--github/--no-github", help="Create a private GitHub repo (no push)."),
) -> None:
    if kind is not None and kind not in KINDS:
        _fail(f"--kind must be one of: {', '.join(KINDS)}")
    if backend is not None and backend not in BACKENDS:
        _fail(f"--build-backend must be one of: {', '.join(BACKENDS)}")
    base = root()
    orgs = workspace_orgs(base)
    if target:
        org, _, name = target.partition("/")
        if org not in orgs:
            _fail(f"Unknown org {org!r}. Known: {', '.join(orgs)}")
        if not NAME_RE.fullmatch(name):
            _fail("Give the project as <org>/<name>, e.g. rijnhardtkotze/tidy")
        if (base / org / name).exists():
            _fail(f"{org}/{name} already exists.")
    else:
        org = _ask_org(orgs)
        name = _ask_name(base, org)
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
        set_authors(base / rel / "pyproject.toml", author, email)
    else:
        (base / rel).mkdir(parents=True)
        run(rel, "git", "init", "-q")
        (base / rel / "README.md").write_text(f"# {name}\n" + (f"\n{description}\n" if description else ""))
    (base / rel / "AGENTS.md").write_text(AGENTS_MD.format(name=name, description=description or "TODO: what this is."))
    (base / rel / "CLAUDE.md").write_text("@AGENTS.md\n")
    # Commits in this repo carry the author given above, whatever the global git config says.
    for key, value in (("user.name", author), ("user.email", email)):
        if value and value != _git_config(key, base / rel):
            subprocess.run(["git", "config", key, value], cwd=base / rel, check=True)

    if not add_to_workspace(base, rel.as_posix()):
        typer.secho("dev.code-workspace already lists it.", dim=True)
    if not add_to_readme(base, org, name, description):
        typer.secho(f"README.md: no `## {org}` table or row already there; add it by hand.", fg=typer.colors.YELLOW)
    config_file = write_path(base)
    if not add_to_config(config_file, name, rel.as_posix(), description):
        typer.secho(
            f"{config_file}: not changed (name {name!r} is taken or the file is not valid TOML); add it by hand.",
            fg=typer.colors.YELLOW,
        )
    if github:
        desc =["--description", description] if description else []
        run(rel, "gh", "repo", "create", f"{org}/{name}", "--private", "--source", ".", "--remote", "origin", *desc)

    typer.secho(f"\nCreated {rel}.", fg=typer.colors.GREEN)
    typer.echo(f"  goto {name}")
    typer.echo('  git add -A && git commit -m "Initial commit"')
