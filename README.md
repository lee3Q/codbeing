# codbeing

Private dogfooding-first User Runtime Simulator.

codbeing is a local-first CLI lab for capturing structured `DecisionTrace`
records and generating evidence-grounded Runtime Analysis reports. The default
runtime stays on the local machine. External model assist is opt-in and only
runs when the user explicitly selects it and a key is available.

## Quick Start

```bash
python3 -m codbeing
python3 -m codbeing example nomusa
python3 -m codbeing capture
python3 -m codbeing run private-traces/decision-traces.json
python3 -m codbeing model status
```

Power-user entrypoints are also available through the local `cb` wrapper when
installed on the machine.

## Privacy Boundary

The repository intentionally excludes local private data:

- `private/`
- `private-traces/`
- `private-reports/`
- `.env` and other secret files

Generated reports and personal trace inputs should remain local unless they are
manually sanitized first.

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
time makes the public replay deterministic. In ordinary use, omit `--at` from
the underlying `predict` command to record the current UTC time. Keep the
prediction file fixed before recording the actual choice. The receipt's
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
