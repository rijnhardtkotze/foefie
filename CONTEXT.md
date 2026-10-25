# foefie

Task runner for the `~/code` workspace. One CLI, so each project's commands are reached the same way.

## Glossary

- **Workspace root**: the nearest directory holding `dev.code-workspace`. Found by searching up from the current directory, then from the installed package location.
- **Project**: a checkout under the workspace root with its own tools, such as `rudderpin` or `concertforge`. Each project is a subcommand group.
- **Command**: one runnable action in a project, such as `rudderpin test`. It runs a program in the project's directory; extra arguments pass through to that program.
- **Suite**: a project's test command. `foefie test` runs every suite and exits with the first failure.
