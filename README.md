# codbeing

Private dogfooding-first User Runtime Simulator.

codbeing is a local-first CLI lab for capturing structured `DecisionTrace`
records and generating evidence-grounded Runtime Analysis reports. The default
runtime stays on the local machine. External model assist is opt-in and only
runs when the user explicitly selects it and a key is available.

## Who this is for

For a person who wants to record one consequential decision, keep its original
reasoning, and later compare it with what happened. A study-plan choice or a
reversible work-priority choice is enough to start. Do not try to log every
micro-decision. Developers can also reproduce the public synthetic cycle.

This is an experimental reflection tool, not a personality test, a validated
predictor of your behavior, or medical, financial, or legal advice. The report's
patterns and hypothesis cards are prompts to check, not facts about a person.
See [user jobs, evidence, and limitations](docs/USER_JOBS_AND_EVIDENCE.md).

## Install and try locally

Requires Python 3.10 or newer. From a downloaded checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
cb --help
cb model status
```

On Windows, activate with `.venv\Scripts\activate` instead. Windows has not
been tested in this change. After installation, `cb` and `python -m codbeing`
work outside the source directory. Records, reports, and configuration are
relative to your current working directory, so choose a private working folder:

```bash
mkdir -p ~/codbeing-private
cd ~/codbeing-private
cb example nomusa
cb capture
cb run private-traces/decision-traces.json
```

The example is a public fixture, not a real prediction. No API key is needed.
For development, run `python -m pip install -e ".[dev]"` in the source checkout.
`sh scripts/verify_installation.sh` builds a wheel and installs it into a second
clean environment, then tests the CLI from outside the checkout. It downloads
Python build tools but does not call model providers.

## Privacy Boundary

The repository intentionally excludes local private data:

- `private/`
- `private-traces/`
- `private-reports/`
- `.env` and other secret files

Generated reports and personal trace inputs should remain local unless they are
manually sanitized first. The ignore rules in this repository do not protect a
separate working folder from its own Git configuration, cloud sync, or backups.

External assist can send the full trace and report after explicit selection and
consent. Dedicated `CODBEING_GLM_API_KEY`, `GLM_API_KEY`, or `ZHIPUAI_API_KEY`
values may be read from the environment, `.env`, or `private/.env`. A generic
`ANTHROPIC_AUTH_TOKEN` and shell startup files are no longer searched. Existing
users of that fallback must deliberately configure a GLM-named key. An explicit
Anthropic-compatible endpoint in the environment or project dotenv still works
with the dedicated GLM key. Do not reuse another provider's credential.

## Reuse status

No repository license was present at the inspected revision. Public visibility
is not an open-source license. Ask the owner to choose a license before claiming
redistribution or reuse rights. No license is selected by this change.

## Public synthetic decision cycle

The [synthetic case](examples/synthetic-cycle/decisions.json) starts with two
directly recorded decisions. The model copies only those reviewed decision
fields; conversation, memo, and behavior material is rejected. A new situation
produces a **hypothesis card** with action, reason, pressure or emotion,
alternatives, confidence, evidence IDs, model version, and prediction time.
The later actual choice is a separate input. This synthetic comparison is a
Stage 1 public reproduction of the workflow. It provides no evidence of
predictive accuracy for a person. Stage 2 research must compare predictions
frozen before real future choices against those later choices; that study is
pending. No old private records are read or migrated.

Run one command from the repository root to generate the model, card, comparison,
and verification receipt from the public synthetic inputs:

```bash
bash scripts/reproduce_synthetic_cycle.sh
python3 -m codbeing.impact_validation examples/synthetic-cycle/validation-graph.json run --receipt-dir .codbeing-validation/public-cycle
python3 -m codbeing.evidence_ledger evidence/public-cycle/ledger.jsonl verify --expected-head 33e0e9424163959e2f0f789b4be7290931c5f2fa1224aa4f6c096639ee2bb686
```

The command prints its temporary output directory. Pass a directory as its
first argument to keep artifacts at a chosen location. Its fixed prediction
time makes the public replay deterministic. That fixed timestamp demonstrates
recalculation, not when a prediction was actually issued. For a new decision,
use the separate prospective journal, which issues a card at the current UTC
time and accepts an actual choice only in a later command:

```bash
python3 -m codbeing.prospective issue examples/synthetic-cycle/decisions.json examples/synthetic-cycle/scenario.json /tmp/my-codbeing-decision
python3 -m codbeing.prospective verify /tmp/my-codbeing-decision
# After making the decision:
python3 -m codbeing.prospective record-actual /tmp/my-codbeing-decision --action "My choice" --reason "Why I chose it"
python3 -m codbeing.prospective verify /tmp/my-codbeing-decision
```

The committed [prospective example](examples/synthetic-prospective/events.jsonl)
uses a **fictional** later choice. Its first event fixes the model and prediction
file hashes before the second event records the choice. Verify its current
chain head with `python3 -m codbeing.prospective verify
examples/synthetic-prospective --expected-head
33de20a4195d436d62e2473f5242111612eb7db83c2ef57946007b49c6197e4f`.
The original issuance head was
`2188ef4f492ba5c3005960ceab2b0b5bbd2ad61117084cb04662e55a0b29f802`.
These local timestamps and hashes demonstrate command order and detect later
file changes when checked against a separately saved head. They do not prove
when a real person chose or make local files tamper-proof without an external
anchor. The deterministic replay receipt's
`passed` field and individual checks show whether the outputs reproduce from
the synthetic inputs.

For a later model build, `conversation`, `memo`, and `behavior` records need the
same decision fields as the synthetic direct decisions, plus `context` and
`meaning` explanations (at least 30 characters each) and a review object:
`{"approved_by_user": true, "reviewed_at": "2026-08-03T12:00:00+00:00"}`.
Without those fields, the build rejects the record. A recorded actual choice
stays separate from the prediction and does not enter the model through
`compare`. To consider it in a later build, explicitly add an `actual_choice`
record with the decision fields, `prediction_id`, `recorded_at`, and a user
review after recording. That build receives a new model ID and v2 version.
The original v1 model and card remain valid; the CLI refuses to replace an
existing model or prediction file with different content. Use new output paths
for each subsequent build and prediction.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 -m pytest -q
```

### DecisionTrace validation

New captures require non-blank text in `context`, `chosen_action` and
`judgment_basis`, and at least one non-blank string in `options`.
`rejected_options` may be empty. Required text fields must be strings;
observations, outcomes and supporting fields may be empty when unknown or
withheld. Validation never fills missing evidence. Extra fields are preserved.

Older key-only files remain readable without rewriting their values. If any
record lacks valid core evidence or field types, analysis returns an
`Insufficient evidence` report with record/field warnings instead of generating
hypotheses, confidence or a Hard Mirror. Back up old files and review the listed
fields; do not invent evidence to make them pass. The `validate` command retains
its legacy key-presence check and does not certify analysis readiness.

Invalid captures and cancellation during input do not append a trace. An
interrupt during saving may occur after the atomic replacement: check the store
before retrying to avoid a duplicate. Writes use a temporary file and atomic
replacement, but concurrent writers are not locked.
