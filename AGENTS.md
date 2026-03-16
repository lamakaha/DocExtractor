# GSD Command Workflow

This repository uses a plain `gsd-*` command workflow interpreted by Codex from prompt text.
These are repo command conventions, not native Codex CLI command registration.

## Supported Commands

- `gsd-help`
  - Show the current GSD status, available commands, and the exact next recommended GSD command.
- `gsd-status`
  - Show phase, active plan, git status summary, and validation state.
- `gsd-next`
  - Return only the next recommended GSD command for this repository.
- `gsd-start <plan-id> <title>`
  - Create or update the next plan artifact in `.planning/phases/...` before implementation.
- `gsd-continue`
  - Continue the active plan from `.planning/STATE.md` and current code state.
- `gsd-close <plan-id>`
  - Run targeted validation, write the summary, update `STATE.md` and `ROADMAP.md`, then commit and push the intended GSD files.

## Execution Rules

- Treat `gsd-*` commands above as the highest-priority user intent for the turn.
- Use the existing `.planning/` workflow as the source of truth.
- For implementation work, update planning artifacts before or alongside code changes when the workflow requires it.
- When a GSD slice is completed and validation passes, commit and push to `origin` unless the user explicitly says not to.
- If the worktree contains unrelated local changes, audit and isolate the intended GSD files instead of bundling everything blindly.

## Mandatory Handoff

- Every completed GSD turn must end with exactly one explicit next-step line in this form:
  - `Next GSD command: gsd-...`
- Do not omit the next command even if the user did not ask for it.
- Prefer concrete commands over prose. Example:
  - `Next GSD command: gsd-start 06-03 multi-page-reconciliation`

## Current Default

- After Phase `06-02`, the next recommended command is:
  - `gsd-start 06-03 multi-page-reconciliation`
