# codbeing Lab UX Official Seed Handoff

Date: 2026-07-17

Purpose: after reboot, regenerate the official Ouroboros Seed for the codbeing lab UX interview in a clean runtime. Do not rely only on `resume-session`; read this handoff first.

## Current User Intent

The user wants this next session to:

1. Keep the manual Seed as an intent snapshot, not as the execution source of truth.
2. Reboot or otherwise start from a clean Ouroboros/Codex runtime.
3. Re-read the completed codbeing UX interview and project context.
4. Regenerate an official Seed through Ouroboros using the `codex` backend, not `zcode`.
5. Compare the official Seed against the intent snapshot before running.
6. Only then run the official Seed.

## Critical Context

Completed interview:

- `interview_20260716_124202`
- State file: `/Users/sanggyulee/.ouroboros/data/interview_interview_20260716_124202.json`
- Status observed in JSON: `completed`

Project:

- `/Users/sanggyulee/codbeing`

Important files to read:

- `/Users/sanggyulee/.claude/projects/-Users-sanggyulee/memory/reference_codbeing.md`
- `/Users/sanggyulee/codbeing/PROJECT_INDEX.md`
- `/Users/sanggyulee/codbeing/UX_REDESIGN_HANDOFF_20260716.md`
- `/Users/sanggyulee/codbeing/LAB_SPACE_SPEC_20260716.md`
- `/Users/sanggyulee/.ouroboros/data/interview_interview_20260716_124202.json`
- `/Users/sanggyulee/codbeing/seed_codbeing_lab_ux_20260716.yaml`
- `/Users/sanggyulee/.ouroboros/seed-revisions/interview_20260716_124202.md`

## What Happened Before This Handoff

The previous session tried the correct Ouroboros path but the runtime was not clean:

- MCP `ouroboros_generate_seed` timed out after 120 seconds.
- MCP `ouroboros_qa` timed out after 120 seconds.
- MCP `ouroboros_session_status` timed out after 120 seconds.
- Process inspection showed multiple `ouroboros mcp serve` processes.
- Two recently spawned Ouroboros MCP server processes were consuming roughly 60% CPU each.
- `ouroboros-zcode` MCP servers were also running from another workstream.
- A `~/ouroboros-zcode` MCP test command was also running, so logs were mixed with test sessions.

Key clarification:

- `FAMILY_PROXY_API_KEY` exists in the current shell and in interactive `zsh`.
- The earlier "missing key" message came from a child `codex` call inside `ooo seed --llm-backend codex`, not from the user's normal shell.
- Treat this as an execution-boundary/runtime contamination problem, not as "the user has no key."

User correction:

- Do not use the `zcode` backend for this task. It is still being ported and is unstable.
- Use the `codex` backend for official generation.

## Manual Seed Status

Manual intent snapshot:

- `/Users/sanggyulee/codbeing/seed_codbeing_lab_ux_20260716.yaml`

This file was created manually by Codex from:

- the completed interview JSON,
- `LAB_SPACE_SPEC_20260716.md`,
- `UX_REDESIGN_HANDOFF_20260716.md`,
- current `codbeing/__main__.py`,
- and same-thread user clarifications.

It is useful as:

- an intent backup,
- a regression-check reference,
- and a comparison target for the official Seed.

It is not the preferred execution artifact because the user has observed that manually generated Seeds tend to fail during `run`.

## Product Decisions That Must Survive Official Seed Generation

The official Seed must preserve these decisions:

1. Running `cb` should feel like entering the codbeing research lab, not a help menu.
2. codbeing is one ongoing study of the current user as code; do not introduce "new research / continue research / choose another research" project UX.
3. Lab surfaces are dynamic. Empty lab state should not show many dead fixed rooms.
4. Self Code, Simulation, Evidence, and Analysis are prepared research apparatus/lenses, not always-visible empty rooms.
5. Initial/empty state should offer first-contact paths: talk with researcher, submit analyzable material, or receive a personalized experiment/question.
6. Researcher accompaniment is global and callable from any surface.
7. The researcher is a docent/commentary/guide layer, not the entire intelligence of the lab.
8. The deeper lab intelligence is a prepared code-based research structure.
9. Use vendor-neutral "LLM assist" language. Do not conceptually hardcode GLM.
10. Solo viewing of refined traces/reports/Self Code/prepared simulations must work without LLM.
11. LLM assist is for free-form interpretation, explanation, new scenario generation, personalized next experiments, and accompanied viewing that needs generative reasoning.
12. When LLM assist views a material, pass the full relevant body/context unless the user explicitly chooses reduced context.
13. External model calls require explicit user selection/key availability and must not silently send private material.
14. Preserve existing power-user commands: `cb capture`, `cb run`, `cb model`, `cb example nomusa`, `cb skills`.

If the official Seed drops or contradicts these points, do not run it yet. Revise or regenerate the official Seed first.

## Next Session Mini Harness

Run after reboot or after intentionally stopping unrelated Ouroboros/OZO work.

```bash
cd /Users/sanggyulee/codbeing
bash scripts/next_session_preflight.sh
```

Expected preflight:

- `FAMILY_PROXY_API_KEY` is present.
- The completed interview JSON exists and reports `completed`.
- The manual intent snapshot exists.
- The existing codbeing tests pass.
- There are no surprising extra `ouroboros mcp serve` processes, or the user intentionally accepts that other OZO/Ouroboros work is running.

Then generate official Seed:

```bash
cd /Users/sanggyulee/codbeing
/Users/sanggyulee/.local/bin/ooo seed interview_20260716_124202 --llm-backend codex
```

If the CLI asks whether to force generation because ambiguity is above threshold, choose force only if the newly generated Seed preserves the decisions above or if the prompt occurs before YAML output and the user still wants generation.

If using MCP instead of CLI, load the seed tool first and call:

```text
ouroboros_generate_seed(session_id="interview_20260716_124202")
```

If MCP calls again time out at 120 seconds for both seed and lightweight status calls, stop and diagnose MCP runtime before continuing.

## Official Seed QA Gate

Before running, compare official Seed against:

- `/Users/sanggyulee/codbeing/seed_codbeing_lab_ux_20260716.yaml`
- the "Product Decisions That Must Survive" section in this handoff

Minimum acceptance for official Seed:

- 3-7 outcome-level acceptance criteria.
- Brownfield context references `/Users/sanggyulee/codbeing`.
- Constraints preserve local-first privacy and legacy CLI commands.
- Ontology includes at least: lab state, research target, evidence/material, work surface/apparatus, researcher accompaniment, and LLM assist policy.
- It does not collapse the UX into a static six-room menu.
- It does not use a project-list model for research.
- It does not make GLM the conceptual provider.

## Run Gate

Only run after official Seed passes comparison.

Preferred route:

```bash
cd /Users/sanggyulee/codbeing
/Users/sanggyulee/.local/bin/ooo run workflow <OFFICIAL_SEED_PATH> --project-dir /Users/sanggyulee/codbeing
```

If using MCP run, first verify lightweight MCP calls work:

```text
ouroboros_session_status(...) or another non-generative status/query call must return quickly.
```

Do not start a long run if basic MCP status still times out.

## Stop Conditions

Stop and ask the user before running if:

- official Seed cannot be generated with `codex`,
- MCP seed/status calls still time out after reboot,
- the official Seed loses core product decisions,
- another OZO/Ouroboros session is intentionally running and process ownership is unclear,
- or the only available Seed is the manual intent snapshot.

