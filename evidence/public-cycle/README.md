# Public decision-cycle evidence

`ledger.jsonl` is a recorded append-only sequence for the fictional case.
It links the Seed, acceptance criterion, executed DAG command, captured
process receipt, five produced artifacts, and handoff. Replay it without
reading model conversation:

```sh
python3 -m codbeing.evidence_ledger evidence/public-cycle/ledger.jsonl verify --expected-head 16693390121e7a5122289f48b5d4de3e7634707f61c6851eb77572eb5ca40c64
python3 -m codbeing.impact_validation examples/synthetic-cycle/validation-graph.json run --receipt-dir .codbeing-validation/public-cycle
```

The graph's run receipts are regenerated locally and intentionally ignored by
Git. `graph-command-receipt.json` and the ledger show what the recorded run
observed. The expected head written here is a convenient check; an external
copy or the published Git commit is needed to detect a coordinated rewrite
of this document and ledger. No personal data is involved.
