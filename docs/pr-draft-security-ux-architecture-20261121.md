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

`python3 -m codbeing.evidence_ledger evidence/public-cycle/ledger.jsonl verify --expected-head 16693390121e7a5122289f48b5d4de3e7634707f61c6851eb77572eb5ca40c64`

## Unknowns

Direct Python 3.10–3.12 coverage, external provider calls, long-running fault injection, and cross-device filesystem behavior were unavailable.

## Rollback

Revert the implementation commit. The revert removes the config mode fix and fixture refresh together with the audit documents and tests.
