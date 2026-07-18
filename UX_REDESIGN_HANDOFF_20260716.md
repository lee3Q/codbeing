# codbeing UX Redesign Handoff

Date: 2026-07-16

Purpose: read this before starting the next `ooo interview` for codbeing UX.

## User Feedback

The current `cb` is usable but not truly user-friendly.

The user wants codbeing to feel less like a set of CLI subcommands and more like opening a game:

```text
type cb once -> enter a smooth terminal experience -> continue naturally
```

Adding commands is not enough. The next iteration should redesign the interaction model.

## Current State

Working executable:

```bash
cb
```

Current commands:

```bash
cb onboard
cb model status
cb model use codex
cb model use glm
cb capture
cb run private-traces/decision-traces.json
cb example nomusa
cb skills
```

Tests:

```bash
cd ~/codbeing
python3 -m unittest discover -s tests -v
```

Current result: `22 tests OK`.

## Current UX Problem

`cb` currently prints state and command suggestions, but it does not become the product surface.

The user still has to remember subcommands and decide what to do next. This feels like a utility, not a smooth dogfooding tool.

## Next Interview Goal

Use `ooo interview` to crystallize:

```text
Redesign codbeing so running cb alone opens a guided terminal product experience where the user can record, analyze, inspect, choose model behavior, reuse examples/session context, and continue to the next action without memorizing commands.
```

## Interview Questions To Explore

- Should `cb` open a dashboard, REPL, numbered menu, or hybrid launcher?
- What should the first screen show when no traces exist?
- What should the first screen show when traces/reports already exist?
- Should the default flow be:
  - record new decision
  - analyze accumulated traces
  - inspect last report
  - continue last thread
  - try Nomusa demo
- Should rough natural-language stories be accepted and structured into DecisionTrace after confirmation?
- Should GLM help draft DecisionTrace fields, and under what consent boundary?
- When should model choice be visible?
- What exactly counts as a “skill” that runs automatically?
- How should existing session/memo context be imported without privacy surprises?

## Likely Acceptance Criteria

- Running `cb` with no args starts an interactive launcher, not just help text.
- The launcher detects whether private traces/reports exist and offers context-aware choices.
- A first-time user can create a trace, generate a report, and locate it without knowing subcommands.
- A returning user can continue from existing traces/reports.
- Model selection is available inside the launcher.
- Existing power-user subcommands still work.
- GLM is never called unless selected and keyed.
- Nomusa example is available as a guided demo from the launcher.
- Tests cover first-run, existing-state, model-selection, and demo launcher paths.

## Preserve Unless Interview Changes It

- Primary executable: `~/.local/bin/cb`
- Legacy executable: `~/.local/bin/codbeing`
- Project root: `~/codbeing`
- Config: `private/codbeing-config.json`
- Trace store: `private-traces/decision-traces.json`
- Reports: `private-reports/`
- GLM detection:
  - `CODBEING_GLM_API_KEY`
  - `GLM_API_KEY`
  - `ZHIPUAI_API_KEY`
  - `ANTHROPIC_AUTH_TOKEN`
  - `.env`
  - `private/.env`
  - `~/.zshrc` `gclaude` values
- GLM call style: direct Anthropic-compatible HTTP, not shelling out to `claude`.

## Important Constraint

Private data is sensitive. Any import from raw session backups, memory files, or personal notes should be explicit and confirmed before model assist sends anything externally.
