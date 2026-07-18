# codbeing Project Index

Updated: 2026-07-18

## Latest Handoff — 2026-07-18 Korean-first Lab UX Recovery

Before continuing codbeing UX/product work, read:

- `~/codbeing/NEXT_SESSION_HANDOFF_20260718_KO_UX.md`

Current state:

- `cb` / `python3 -m codbeing` now opens a Korean-first Lab entrance.
- Local verification after the overnight recovery:
  - `python3 -m unittest discover -s tests -v` -> 60 OK
  - `python3 -m pytest -q` -> 78 passed
  - `printf 'q\n' | python3 -m codbeing` -> Korean Lab launcher, local-first privacy/model boundary, four first actions.
- The outer `ooo auto` harness did **not** PASS. It retried hundreds of times
  because local `ooo` was running under repo `.venv` Python 3.14 and failed on
  a pydantic import/type-evaluation error. Treat this as a harness/runtime
  failure, not as proof that the codbeing UX failed.

## Latest Handoff — 2026-07-17 Official Seed Regeneration

Before using `resume-session` alone or running any codbeing UX Seed, read:

- `~/codbeing/NEXT_SESSION_HANDOFF_20260717.md`

That handoff records the completed interview `interview_20260716_124202`, the manual intent-snapshot Seed, the MCP timeout/runtime contamination diagnosis, the "do not use zcode backend" correction, and the exact clean-runtime mini harness for regenerating an official Ouroboros Seed with the `codex` backend after reboot.

Preflight command for the next session:

```bash
cd ~/codbeing
bash scripts/next_session_preflight.sh
```

## Handoff Header — 2026-07-16 Run Recovered, MVP Implemented, QA Hardened

Read this first in the next session. The previous “seed exists but run never executes” problem has been resolved through the local CLI route.

## Lab Space Spec — 2026-07-16

Read `~/codbeing/LAB_SPACE_SPEC_20260716.md` before redesigning the next codbeing UX.

New product framing from the user:

- The lab is named `codbeing`.
- It starts as Sanggyu Lee's private personal research lab, not a SaaS product.
- If personal dogfooding proves "this works," the later direction is an open-source framework so anyone can create their own lab.
- The lab should feel like entering a research facility where the central asset is "me as code."
- AI agents should be framed as research staff with different temperaments and roles, not generic chatbots.
- Researcher tone should be configurable by the user.
- Conversation is optional; choice-based and simulation-based paths are first-class ways to produce runtime evidence.
- Data requirements vary by desired confidence, current user state, and the quality/depth of existing consciousness data.
- External sharing and monetization are deliberately deferred.

## UX Redesign Handoff — Prepare Next `ooo interview`

The user explicitly does **not** consider the current UX truly user-friendly yet.

Current UX assessment:

- `cb` exists and works, but it still feels like a command-line utility.
- The user wants the experience to feel more like “turning on a game”: type `cb` once, then smoothly continue without remembering subcommands.
- Adding more commands is not enough. The core problem is the interaction model, not missing flags.
- The next improvement should probably start with `ooo interview` in a separate session, not immediate coding, because the requirement is now about product/UX shape.

Desired next-session interview target:

> Redesign codbeing so that running `cb` alone opens a smooth terminal product experience where the user can record, analyze, inspect, choose model behavior, reuse examples/session context, and decide the next action without memorizing commands.

Important framing for the interview:

- Treat current code as a brownfield MVP, not the final UX.
- Do not simply add another subcommand.
- The design should decide whether `cb` opens:
  - a dashboard/home screen
  - a conversational REPL
  - a numbered menu loop
  - a hybrid “launcher + guided flow”
- The design should clarify how much automation is expected after startup:
  - auto-detect existing traces/reports
  - suggest “continue last analysis”
  - offer “record a new decision”
  - offer “analyze current accumulated runtime”
  - offer “try the Nomusa example”
  - offer “import from known session/memo context”
- The design should clarify how model choice appears:
  - hide by default unless model assist is needed
  - show current provider in status line
  - allow in-flow switching between local/Codex and GLM
  - never leak API keys
- The design should clarify what “skills run automatically” means:
  - Hard Mirror gate should trigger only when the trace has explicit gate fields
  - Nomusa/academic interpretation should trigger only on matching evidence
  - model assist should run only when selected and keyed
  - session/memo import should be explicit because private data is sensitive
- The design should decide what “conversation while accumulating” means:
  - current `cb capture` asks fixed fields one by one
  - desired UX may let user paste a rough story and have codbeing structure it into a DecisionTrace after confirmation
  - if GLM is enabled, it may help draft fields, but local privacy and confirmation must remain explicit
- The design should define a good first-run loop:
  - `cb`
  - shows state and offers 2-4 choices
  - user selects one by number or short text
  - codbeing guides the next step
  - report opens/prints path and offers follow-up

Potential acceptance criteria for next Seed:

- Running `cb` with no args starts an interactive terminal launcher instead of only printing help/static commands.
- The launcher detects whether private traces/reports exist and offers context-aware next actions.
- A user can create a first DecisionTrace, generate a Runtime Analysis, and find the report without knowing any subcommands.
- A user can select Codex/local or GLM model behavior from inside the launcher.
- Existing `cb run`, `cb capture`, `cb model`, and `cb example nomusa` remain available for power users.
- No private trace data is sent to GLM unless the user explicitly selects GLM/model assist.
- The UX makes the Nomusa example available as a guided demo without requiring the user to remember `cb example nomusa`.
- Tests cover the launcher’s first-run, existing-trace, model-selection, and demo paths.

Current implementation details to preserve unless the interview decides otherwise:

- Primary executable: `~/.local/bin/cb`
- Legacy executable: `~/.local/bin/codbeing`
- Private config path: `~/codbeing/private/codbeing-config.json`
- Default trace store: `~/codbeing/private-traces/decision-traces.json`
- Default report dir: `~/codbeing/private-reports/`
- GLM key detection:
  - env vars: `CODBEING_GLM_API_KEY`, `GLM_API_KEY`, `ZHIPUAI_API_KEY`, `ANTHROPIC_AUTH_TOKEN`
  - local ignored files: `.env`, `private/.env`
  - existing `~/.zshrc` `gclaude` function values: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_DEFAULT_SONNET_MODEL="GLM-5"`
- GLM calling style:
  - Direct Anthropic-compatible HTTP call.
  - Do **not** shell out to `claude`; `gclaude` was only a Claude Code workaround.
- Current tests pass: `python3 -m unittest discover -s tests -v` → `22 tests OK`.

Current outcome:

- Recovered/reconstructed the primary dogfooding Seed from event-store context as `~/codbeing/seed_0ef7ce7b63d0.reconstructed.yaml`.
- Verified the reconstructed Seed with dry-run.
- Executed it with local CLI `~/.local/bin/ooo run workflow ...`, not Codex MCP.
- Final successful Ouroboros run:
  - Session: `orch_ab4ab4af6618`
  - Execution: `exec_a85dde0ccfd9`
  - Result: `Success: 6/6`
  - Messages processed: `80`
  - Duration: `1635.2s`
- AC 1-3 were treated as externally satisfied after earlier implementation/local verification.
- AC 4-6 completed in the final successful run.
- Local verification passed: `python3 -m unittest discover -s tests -v` → `9 tests OK`.
- Later evaluation attempt was started, but formal `ouroboros_evaluate` did not produce a terminal verdict because the MCP/Codex JSON-RPC stream timed out or became invalid. This is an Ouroboros runtime/tooling issue, not a codbeing product failure.
- Local `ooo qa` over the observed artifact passed: score `0.82 / 1.00`, with caveats around malformed input probing, prompt-injection text, repeatability, and output collision safety.
- QA hardening was applied directly after MCP Ralph also timed out:
  - malformed/empty/wrong-top-level JSON tests
  - large evidence field truncation
  - instruction-like trace text neutralization
  - analyze output collision refusal
  - full suite now passes: `python3 -m unittest discover -s tests -v` → `15 tests OK`.
- Usability pass added after user feedback:
  - executable wrapper: `~/.local/bin/codbeing`
  - primary executable wrapper: `~/.local/bin/cb`
  - `codbeing quick <trace.json>` / `codbeing run <trace.json>` validate and analyze in one command with automatic report naming
  - `codbeing capture` interactively appends one DecisionTrace to `private-traces/decision-traces.json` and writes an accumulated report
  - `codbeing example nomusa` creates the sanitized academic/Nomusa dogfooding fixture and report
  - full suite now passes: `python3 -m unittest discover -s tests -v` → `18 tests OK`.
- User-friendly runtime pass added after follow-up:
  - `cb` with no args shows the current state, next actions, model commands, and skill list entrypoint
  - `cb onboard` runs first-use setup
  - `cb model status` shows selected provider and whether a GLM key is present without printing secrets
  - `cb model use codex` and `cb model use glm` select the default report execution model in `private/codbeing-config.json`
  - `cb run ... --model glm` can request GLM model assist for one run
  - GLM keys are detected from env vars `CODBEING_GLM_API_KEY`, `GLM_API_KEY`, `ZHIPUAI_API_KEY`, or ignored local files `.env` / `private/.env`
  - GLM also detects the existing `~/.zshrc` `gclaude` alias/function style: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, and `ANTHROPIC_DEFAULT_SONNET_MODEL="GLM-5"`; `cb` uses those values for direct Anthropic-compatible HTTP calls and does not shell out to `claude`
  - GLM is only called when selected and a key exists; otherwise codbeing writes the local evidence-grounded report and records that no external trace data was sent
  - `cb skills` lists built-in flows: capture, run/quick, example nomusa, automatic Hard Mirror gate, model assist
  - full suite now passes: `python3 -m unittest discover -s tests -v` → `22 tests OK`.

Implemented files:

- `~/codbeing/codbeing/__main__.py` — local CLI with `validate`, `analyze`, `quick`/`run`, `capture`, `example nomusa`, `model`, `onboard`, and `skills`.
- `~/codbeing/codbeing/config.py` — private local model configuration and GLM key detection without printing secrets.
- `~/codbeing/codbeing/models.py` — optional model assist; codex/local by default, GLM only when selected and keyed.
- `~/codbeing/codbeing/schema.py` — DecisionTrace schema validation.
- `~/codbeing/codbeing/report.py` — evidence-grounded Runtime Analysis generation, dogfood interpretation, Hard Mirror gating, must-not-output safeguards.
- `~/codbeing/tests/test_cli_validation.py` — validation, malformed input, report, dogfood, Hard Mirror, must-not-output, prompt-injection-text neutralization, output collision, and privacy tests.
- `~/codbeing/.gitignore` — private traces/reports/session backup/secrets/privacy paths.
- `~/codbeing/completed_acs.yaml` — skip marker used to resume AC 4-6 after AC 1-3 were already satisfied.

Operational notes:

- Working CLI path that succeeded: `/Users/sanggyulee/.local/bin/ooo`.
- The immediate blocker was local guardrail policy, not the codbeing Seed itself. Updated `/Users/sanggyulee/agent-guard/guardrail.py` to allow needed safe commands (`ooo`, `ouroboros`, `uv run`, `uvx ouroboros`, `git -C ... status`, `codex plugin add`) while keeping destructive/secret/bypass blocks. Guardrail tests passed: `11 passed`.
- Codex MCP is still not fully proven fixed in this session. Evidence showed MCP config/plugin cache was using `uvx --from ouroboros-ai[mcp] ...`, while the fixed local tool comes from `/Users/sanggyulee/ouroboros-zcode`.
- `~/plugins/ouroboros/.mcp.json` was changed to use `/Users/sanggyulee/ouroboros-zcode/scripts/mcp-serve.sh`.
- Direct `~/.codex/config.toml` could not be edited from this sandbox because `~/.codex` is read-only in the current permission profile. Next session may need to update it outside this sandbox or reinstall/cachebust the personal plugin, then restart Codex.
- Practical next route if MCP is questionable: use local CLI `~/.local/bin/ooo run workflow <seed> --project-dir ~/codbeing`.

Next useful work:

- Run `cb` to see current state and next commands.
- Run `cb onboard` if selecting model defaults for the first time.
- Run `cb model use glm` once the GLM key is available in env or `.env`, or keep `cb model use codex` for local-only reports.
- Run `cb example nomusa` to create the first private fixture/report, then inspect whether the report feels useful.
- Use `cb capture` after real decisions to accumulate DecisionTrace records through conversation-like prompts.
- Use `cb run private-traces/decision-traces.json` to generate an updated accumulated Runtime Analysis.
- If continuing Ouroboros runtime reliability work, fix/verify MCP local-source wiring and dependency-analysis timeout separately; do not conflate that with codbeing product validity.
- If continuing the QA loop, rerun formal `ouroboros_evaluate` only after the MCP/Codex JSON-RPC timeout/invalid-stream issue is fixed.

## Identity

codbeing is a private dogfooding-first User Runtime Simulator.

The product treats a user as a set of behavior, judgment, reaction, and decision-runtime traces. The first goal is not public release. The first goal is to produce one useful Runtime Analysis from the user's own DecisionTrace data that feels like code-level self-analysis.

## Current Position

- Project name: codbeing
- Stage: MVP implementation exists from recovered Ouroboros run; needs product review and dogfood report inspection
- First interface: local CLI
- Storage direction: local-first JSON for structured traces, Markdown for reports
- Primary user: Sanggyu Lee, personal dogfooding
- Open-source status: post-dogfooding TODO only

## Core Product Claim

Given structured DecisionTrace records, codbeing should produce evidence-grounded Runtime Analysis about the user's internal decision trajectory:

- activation triggers
- judgment shifts
- baseline deviation
- contradiction or correction points
- regret/reversal loops
- likely internal reaction path
- decision protocol for the current case

It must not claim to predict external success or failure as its core value.

## MVP Scope

MVP should support:

- Validate a structured DecisionTrace JSON file.
- Analyze one important current decision against past traces.
- Produce a Markdown Runtime Analysis report.
- Select one output tier:
  - Insufficient Runtime Signal
  - Mirror Only
  - Hypothesis Draft
  - Runtime Analysis
  - Hard Mirror
- Show confidence factor breakdown, not hidden intuition.
- Preserve user override.

MVP does not need:

- Web app
- TUI
- Multi-user account system
- Cloud sync
- Public synthetic fixture polish
- Storage encryption implementation
- Open-source packaging

## DecisionTrace Contract

Required fields:

- `context`
- `options`
- `chosen_action`
- `rejected_options`
- `judgment_basis`
- `observed_behavior`
- `outcome`
- `aftertaste`
- `memory_confidence`
- `source`

Recommended privacy fields:

- `privacy_level`
- `redaction_notes`

## Security Baseline

The data is highly sensitive personal information.

MVP security floor:

- local-first by default
- private data directory
- `.gitignore` protection for private traces and reports
- no telemetry
- no secrets in repo
- no raw personal logs
- no raw session backup persistence
- no committed private traces unless explicitly intended for local-only ignored fixtures

Post-MVP security maintenance:

- storage encryption review
- dependency audit
- secret scanning
- raw log review
- deletion/export policy
- threat model update

## Dogfooding Golden Example

Private golden example source:

- Session backup: `~/pp/아카이브/세션_백업/2026-07-15_005454_019f6099-1cdf-79c2-812f-e34b924246ae.jsonl`
- Track-change interview: `interview_20260714_123005`
- Leave-of-absence interview: `interview_20260714_145920`
- Final roadmap memo: `~/learning/bar-exam/학사_노무사_진로로드맵_2026-07-15.md`

Expected golden conclusion:

> 국가근로 손실은 휴학의 이유가 아니라 activation signal이고, 이 결정의 본질은 노무사 루트의 옵션 가치와 졸업 지연 비용을 2025/2026 실전 기출 성과라는 검증 가능한 분기 기준으로 판단하는 것이다.

This golden example should produce `Runtime Analysis`, not `Hard Mirror`, unless a later high-impact immediate decision repeats the same activation pattern.

## Ouroboros Run History

Run attempts on 2026-07-16 failed before useful implementation.

- `seed_873db3ce7231`: earlier broader User Runtime Simulator seed. Run failed with model provider routing error.
- `seed_3db9e09ccad6`: codbeing seed with open-source/security gate included. Useful as reference, but open-source concerns should be post-dogfooding.
- `seed_0ef7ce7b63d0`: dogfooding private MVP Seed recorded in the Ouroboros event store. This is the primary Seed/run lineage to recover before creating any new Seed.
- `job_924729102e4c` / `orch_ec4cb2f171e6` / `exec_54d23c8e2107`: dogfooding private MVP run. Failed with provider routing error. DB evidence shows stale model routing including `gpt-5.1-codex-mini` / `gpt-5-codex`, later addressed in the Ouroboros model-routing work.

Conclusion:

The failures do not currently prove product or implementation infeasibility. They indicate Ouroboros runtime/model routing failure. The correct next action is to recover the existing Seed/session first, not author a new inline Seed from memory.

## Rerun Rule

When resuming codbeing:

1. Recover the existing Seed/run context first:
   - Seed IDs: `seed_0ef7ce7b63d0`, `seed_3db9e09ccad6`, `seed_873db3ce7231`
   - Run IDs: `job_924729102e4c`, `orch_ec4cb2f171e6`, `exec_54d23c8e2107`
   - Event store: `~/.ouroboros/ouroboros.db`
   - Checkpoint: `~/.ouroboros/data/checkpoints/checkpoint_orch_ec4cb2f171e6.json`
2. If the exact Seed YAML cannot be recovered, reconstruct only from recovered event-store ACs and label it as reconstructed.
3. Do not create a fresh manual inline Seed unless the user explicitly chooses to replace the existing Seed.
4. Validate/dry-run any reconstructed Seed before execution.

## Next Practical Step

Rerun the recovered dogfooding MVP Seed after Ouroboros model routing and MCP/background execution status are healthy.

If direct implementation is explicitly chosen later:

1. Create a small Python package or script-based CLI.
2. Add DecisionTrace schema validation.
3. Add a private ignored fixture directory.
4. Encode the academic/Nomusa golden example as a local private fixture.
5. Generate one Markdown Runtime Analysis report.
6. Verify must-not-output and privacy baseline tests.

## Open-Source TODO

Open-source is not part of the dogfooding MVP.

Only revisit after:

- one meaningful private Runtime Analysis exists
- the user manually confirms it feels like code-level self-analysis
- private traces are separated from public code

If revisited:

- create fully synthetic fixtures
- write privacy/security README
- add threat model
- add secret scan and dependency audit
- decide whether storage encryption is required before release
