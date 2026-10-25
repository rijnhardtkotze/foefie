# 2. Commands come from a TOML config

Status: accepted

## Context

Every project and command was written as Python in `cli.py`. Adding a project meant editing code, and the list of commands could not be checked without reading it.

## Decision

Projects and commands live in `foefie.toml` at the workspace root, and the CLI builds its subcommands from it at start-up. `FOEFIE_CONFIG` overrides the path. With no file, foefie uses the bundled `foefie.example.toml`, which holds the 16 commands of v0.1.

The format is TOML, read with the standard library `tomllib`:

- No dependency, and it is already the format of `pyproject.toml` and `mise.toml` here.
- Commands are argument lists, not shell strings, so nothing is quoted or expanded by a shell.
- YAML needs a parser and has implicit typing. JSON has no comments. Python config would put code back in the file this decision removes it from.

The loader rejects unknown keys and wrong types, and every error names the file and the key, such as `commands[2].project`.

## Consequences

- Python 3.11 or later is required for `tomllib`; the project already requires 3.12.
- A new project needs no code change. Behaviour that is not a program in a directory (the `foefie new` wizard) stays in Python.
- The config is read when the CLI starts, so a broken `foefie.toml` stops every command until it is fixed. The error says where.
- `test_example_config_matches_v0_commands` pins the bundled commands, so changing one is a visible edit.
