# PR draft — security and UX architecture audit

## Summary

Implement confirmed F-002 config permissions and repair the public evidence ledger fixture contract. Preserve the built-in `open()` report writer compatibility fix.

## Changes

- Atomically write config files with owner-only mode `0600`.
- Add regression coverage for umask `022`, overwrite semantics, and resulting mode.
- Align the report race regression seam with the built-in `open()` implementation.
- Regenerate the public ledger using observed attempt-aware receipts.
- Update the public expected head and add audit evidence.

## Verification

`uv run --with pytest pytest -q`

`scripts/verify_installation.sh`

`bash scripts/reproduce_synthetic_cycle.sh`

`python3 -m codbeing.evidence_ledger evidence/public-cycle/ledger.jsonl verify --expected-head 96a83068d6ee42fe2f65b323830de46e4fde29008217bfeb5501f92707ed5d3b`

## Unknowns

Direct Python 3.10–3.12 coverage, external provider calls, long-running fault injection, and cross-device filesystem behavior were unavailable.

## Rollback

Revert the implementation commit. The revert removes the config mode fix and fixture refresh together with the audit documents and tests.
