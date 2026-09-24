# AC 3 handoff

The evidence ledger is implemented in `codbeing/evidence_ledger.py`, with
usage in `docs/evidence-ledger.md` and verification in
`tests/test_evidence_ledger.py`. The ledger for this AC is `evidence/ac3.jsonl`.
Its `run` event executed the test command and recorded the process exit code,
output, and command link in `evidence/ac3-test-receipt.json`. Replay with
`python3 -m codbeing.evidence_ledger evidence/ac3.jsonl verify`. Keep its
final head hash independently to detect a valid-tail deletion.
