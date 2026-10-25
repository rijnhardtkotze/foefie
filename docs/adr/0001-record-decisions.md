# 1. Record decisions as ADRs

Status: accepted

## Context

foefie is rebuilt in stages. Choices such as config format, supported Python version and what the tool will not do need a place to live that outlasts a PR thread.

## Decision

Record each hard-to-reverse decision as a short ADR in `docs/adr/`, numbered in order (`0001-title.md`) with Context, Decision and Consequences. Use the terms in `CONTEXT.md`.

## Consequences

A later change can read why something was done before undoing it. Superseded ADRs stay in place with their status changed.
