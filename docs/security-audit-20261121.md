# Security audit implementation — 2026-11-21

## Confirmed findings

- **F-002, medium**. New config files could be created as `0644` under umask `022`, exposing private settings to group and other users.
- **C-02**. The committed public evidence ledger used a legacy passing receipt shape that the current verifier correctly rejects because it lacks observed attempt provenance.

## Patch rationale

`save_config()` now writes through a same-directory temporary file, sets mode `0600`, flushes and fsyncs the file, then atomically replaces the destination. This preserves overwrite semantics while making newly written configuration owner-only. Existing report-writer compatibility using built-in `open(..., opener=...)` is preserved.

The public cycle ledger was regenerated through `EvidenceLedger.run()`. Its receipt now contains the observed attempt, inputs, outputs, exit status, stdout, stderr, and outcome required by the verifier. The committed expected head was updated to the regenerated head. Verifier safety was not weakened.

## Review remediation

The follow-up repair moved the public ledger outputs to the tracked synthetic-cycle example files and regenerated the observed graph-command receipt through EvidenceLedger.run(). The exact verification command now reports current_status.public_cycle: PASS with expected head 96a83068d6ee42fe2f65b323830de46e4fde29008217bfeb5501f92707ed5d3b. A regression test asserts the semantic status and head.

## Tests and evidence

- Focused config permission and overwrite tests passed.
- Focused report no-clobber tests passed, including race, symlink, owner-only, and overwrite behavior.
- `uv run --with pytest pytest -q` passed.
- `scripts/verify_installation.sh` passed.
- Synthetic cycle passed.
- Public ledger verification with the README expected head passed.

## Unknowns

Python 3.10–3.12 and external provider calls were not available for direct execution on this host. Long-running multi-process fault injection and cross-device behavior remain untested.

## Rollback

Revert the implementation commit. This restores the previous config writer and public fixture. The report-writer compatibility fix is part of the preserved working change and should be reverted only if the full commit is intentionally rolled back.
