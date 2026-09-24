#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case_dir="$repo_root/examples/synthetic-cycle"
output_dir="${1:-$(mktemp -d "${TMPDIR:-/tmp}/codbeing-synthetic.XXXXXX")}"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"

cd "$repo_root"
python3 -m codbeing.research_cycle model "$case_dir/decisions.json" "$output_dir/model.json"
python3 -m codbeing.research_cycle predict "$output_dir/model.json" "$case_dir/scenario.json" "$output_dir/prediction.json" --at 2026-08-01T12:00:00+00:00
python3 -m codbeing.research_cycle compare "$output_dir/prediction.json" "$case_dir/actual.json" "$output_dir/comparison.json"
python3 -m codbeing.research_cycle verify "$case_dir/decisions.json" "$case_dir/scenario.json" "$case_dir/actual.json" "$output_dir/model.json" "$output_dir/prediction.json" "$output_dir/comparison.json" "$output_dir/receipt.json"

# Run the real project graph, then record the observed command and its
# artifacts in a fresh append-only ledger. Each invocation gets a new ledger.
mkdir -p "$repo_root/.codbeing-runs"
ledger_dir="$(mktemp -d "$repo_root/.codbeing-runs/run.XXXXXX")"
ledger_rel="${ledger_dir#"$repo_root"/}/evidence.jsonl"
receipt_rel="${ledger_dir#"$repo_root"/}/graph-command-receipt.json"
python3 -m codbeing.evidence_ledger "$ledger_rel" record seed --file examples/synthetic-cycle/seed.json > /dev/null
python3 -m codbeing.evidence_ledger "$ledger_rel" record acceptance_criterion --ac-id public_cycle --text 'Synthetic decision cycle, validation DAG, and artifact-backed completion' > /dev/null
python3 -m codbeing.evidence_ledger "$ledger_rel" run --ac-id public_cycle --receipt "$receipt_rel" -- python3 -m codbeing.impact_validation examples/synthetic-cycle/validation-graph.json run --receipt-dir .codbeing-validation/public-cycle > /dev/null
for artifact in model.json prediction.json comparison.json receipt.json validation-graph.json; do
  python3 -m codbeing.evidence_ledger "$ledger_rel" record artifact --ac-id public_cycle --file "examples/synthetic-cycle/$artifact" > /dev/null
done
python3 -m codbeing.evidence_ledger "$ledger_rel" record handoff --ac-id public_cycle --file examples/synthetic-cycle/handoff.md > /dev/null
python3 -m codbeing.evidence_ledger "$ledger_rel" verify > "$ledger_dir/verified-state.json"

printf 'Stage 1 synthetic artifacts: %s\n' "$output_dir"
printf 'Evidence ledger and replayed state: %s\n' "$ledger_dir"
