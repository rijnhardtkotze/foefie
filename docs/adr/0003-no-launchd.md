# 3. No launchd: foefie is a CLI, not a service

Status: accepted

## Context

The rebuild standard includes launchd packaging for tools that run as services. foefie starts, runs one command in a project directory and exits. It listens on nothing and keeps no state between runs.

## Decision

Do not ship a launchd agent, plist or install task. foefie is installed and run on demand, through `uv run foefie` or `mise run dev`.

## Consequences

- No background process, log files or restart logic to maintain.
- Long-running programs such as `rudderpin serve` and `website dev` are started in the foreground by the person who wants them, and belong to their own projects.
- If foefie ever needs to act on a schedule or watch files, that is a new decision and a new ADR.
