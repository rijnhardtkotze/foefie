# Changelog

All notable changes are recorded here. Entries are built from the fragments in
`changelog.d/` with [towncrier](https://towncrier.readthedocs.io/).

<!-- towncrier release notes start -->

## 0.2.0 (2026-10-25)

### Added

- Projects and commands now come from `foefie.toml` in the workspace root, validated with errors that name the file and key. `FOEFIE_CONFIG` overrides the path, and without a file foefie uses the bundled `foefie.example.toml`, which holds all 16 v0.1 commands. The hard-coded command definitions are gone from `cli.py`. ([#10](https://github.com/rijnhardtkotze/foefie/issues/10))
- `foefie new` starts a project: it asks for the org, name, type, Python version, build backend and author, runs `uv init`, lists the folder in `dev.code-workspace` and the README, optionally creates a private GitHub repo (no push), and now also appends the project to `foefie.toml` (created from the bundled example if missing; existing entries are never changed). The wizard lives in its own `foefie.new` module. ([#11](https://github.com/rijnhardtkotze/foefie/issues/11))

### Changed

- Split the CLI into `workspace`, `runner` and `cli` modules, require Python 3.12 and add pytest, ruff, towncrier and mise `test`, `lint` and `ci` tasks. Behaviour is unchanged. ([#8](https://github.com/rijnhardtkotze/foefie/issues/8))

### Fixed

- `foefie test` now runs every suite even when one project directory or tool is missing, and exits with the first failure. Added tests for the runner's exit codes (2 for a missing directory, 127 for a missing tool, the subprocess status otherwise) and argument pass-through. ([#9](https://github.com/rijnhardtkotze/foefie/issues/9))
