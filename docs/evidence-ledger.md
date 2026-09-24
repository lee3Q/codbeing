# Evidence ledger

The ledger is a local JSON Lines file. Each append stores the previous event
hash, its own SHA-256 hash, and the SHA-256 of any referenced file. It records
the Seed, criterion text, executed command, test receipt, artifact, and handoff
in that order. Events for separate criteria can be interleaved; each event
points to its criterion. Receipts point to commands, artifacts to passing
receipts, and handoffs to artifacts. `verify` replays the file to derive each
criterion's status (`registered`, `command_recorded`, `failed`, `verified`, or
`handed_off`) and checks every hash and referenced file.

From the workspace root, for example:

```bash
python3 -m codbeing.evidence_ledger evidence.jsonl record seed --file seed.yaml
python3 -m codbeing.evidence_ledger evidence.jsonl record acceptance_criterion --ac-id 3 --text 'Record hashed evidence lineage'
python3 -m codbeing.evidence_ledger evidence.jsonl run --ac-id 3 --receipt test-receipt.json -- python3 -m pytest -q
python3 -m codbeing.evidence_ledger evidence.jsonl record artifact --ac-id 3 --file result.txt
python3 -m codbeing.evidence_ledger evidence.jsonl record handoff --ac-id 3 --file handoff.md
python3 -m codbeing.evidence_ledger evidence.jsonl verify
```

`run` executes the argv vector and captures stdout, stderr, and exit status.
A caller cannot turn a command string and a claimed `passed=true` into a
verified state. Keep the receipt file unchanged after recording it.

Record the final `head` hash outside the ledger, then pass it to `verify
--expected-head HASH`. This detects deletion of a valid tail. File and event
edits are detected on replay. As with any local hash chain, a person who can
rewrite the whole ledger and its files can forge a new chain unless the head
hash has been anchored independently. Keep personal evidence local; only
publish sanitized files intentionally.
