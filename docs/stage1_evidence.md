# Codbeing Stage 1 evidence review

This successor starts from public HEAD `0757f2b89c84f822e85da717c7090e140b2ccf73`
in the isolated `auto_94519b02848e` worktree. The dirty `codbeing` checkout,
the terminal `auto_0459d9e3b462` worktree, and earlier evidence were preserved.
Nothing from this worktree was merged, published, or pushed.

## Positive verification contract

Each command below exits zero only when its assertions pass. The intentionally
nonzero failure DAG CLI is a *subject* of the AC2 and AC4 checks, never a
`verify_command` or a success receipt.

| AC | Expected test or script artifact | Positive verification command |
| --- | --- | --- |
| 1: subprocess receipts and integrity | `tests/test_stage1_receipts.py`, `tests/test_evidence_ledger.py` | `python3 -m pytest -q tests/test_stage1_receipts.py tests/test_evidence_ledger.py` |
| 2: A → B, independent C | `tests/test_stage1_dag.py` | `python3 -m pytest -q tests/test_stage1_dag.py` |
| 3: prospective card and later actual choice | `tests/test_stage1_prospective_cycle.py` | `python3 -m pytest -q tests/test_stage1_prospective_cycle.py` |
| 4: reviewable fresh evidence | `scripts/verify_stage1_review.py`, this document | `python3 scripts/verify_stage1_review.py --out '/Users/sanggyulee/H/01_프로젝트/resume-repo-alignment/2026-09-24_session/03_evidence/codbeing-stage1-final5-20260925'` |

The full project gate is `python3 -m pytest -q`. It passed with **132 tests and
17 subtests** on this successor worktree. The focused receipts, DAG and prospective
command passed **40 tests** twice. The AC4 review command above exited zero and wrote new,
named synthetic artifacts. Its failure child CLI exited 7 as required; that
child command was not recorded as a successful verification. Running the same
review command again checks the saved ledgers and prospective files without
overwriting them. A new output directory creates another fresh run.

The AC1–AC3 test artifacts and code were inherited from accepted work in this
same isolated worktree. The files changed in the AC4 attempt are
`scripts/verify_stage1_review.py` and `docs/stage1_evidence.md`. The external
review directory and independent verdict are separately named new evidence,
not workspace files. No inherited, untouched code file is claimed as touched
by AC4.

## What the evidence actually shows

`EvidenceLedger.run` launches its recorded argv in a subprocess. The command
event and test receipt bind an attempt ID, command-event hash, input SHA-256,
declared output paths and output SHA-256, actual exit code, stdout, stderr, and
outcome. It appends Seed, AC, command, test receipt, artifact, invalidation,
and handoff events. Replay validates the event chain, receipt links, current
inputs and outputs, and dependency-derived status. Failed exits, timeouts,
interruptions, missing outputs, stale outputs, and changed outputs cannot
restore an earlier PASS. Tests cover these boundaries, and historical attempt
records remain in the ledger. A changed receipt is rejected as broken evidence.

The new review directory contains `failure/` and `success/` ledgers, receipts,
inputs and outputs, plus `failure-result.json`, `success-result.json`,
`prospective-result.json`, and `review-summary.json`. The positive review script
replays each ledger with its head, checks status and attempt counts, and checks
that C's receipt ID and SHA-256 stay unchanged *within each run*.

| Snapshot | A | B | C | A/B/C attempt counts |
| --- | --- | --- | --- | --- |
| Initial v1, both paths | PASS | PASS | PASS | 1/1/1 |
| After A input changes to v2, before rerun | INVALID | INVALID | PASS | 1/1/1 |
| After A v2 subprocess exits 7 | FAIL | BLOCKED | PASS | 2/1/1 |
| Separate successful A/B v2 rerun | PASS | PASS | PASS | 2/2/1 |

The failed A receipt contains exit code `7`, stdout `""`, stderr `"boom\n"`,
and no `a.txt` output hash. There is no B v2 receipt in that branch. C's
original artifact SHA-256 is
`caa6334e09dd1d86c17e572191d57c8a1c43431884ce02ccb92d3e7e2e6d18ef`.
The failure and success branches are separate fresh runs, so their C receipt
IDs differ across branches; each branch preserves its own C receipt ID.

The prospective directory records a synthetic card before a separately
entered actual choice. The card contains expected action, reason,
pressure/emotion, alternatives, confidence, model version, evidence IDs, and
issuance time. Verification first returned `awaiting_actual`, then `compared`;
the unchanged card hash and event chain connect those steps. The current model
uses past synthetic decisions and a simple selection rule. This validates the
workflow, not predictive accuracy for the real user. The user's actual
decisions and any contextual material require their own consent and detailed
explanation before they can become model evidence.

The local ledger is append-only under its own hash chain. An attacker able to
rewrite the full local ledger and all receipts can create a new internally
consistent history. Detecting that requires an independently stored prior head
hash as an external anchor. Local timestamps alone do not prove when a person
made a choice.

The latest verifier rejects a handoff after invalidation until a fresh passing
receipt and artifact appear. `run()` has a 300-second default timeout with a
3600-second maximum and will not remove an existing output. An unchanged old
output cannot satisfy a new attempt. Unknown execution after a command event
without a receipt blocks automatic retry; if a completed receipt exists,
retrying that same receipt path validates and appends it without rerunning the
command. The synthetic DAG requires an empty output directory so it cannot
overwrite existing user files. Passing process receipts cannot be added through
the public `append()` method. Receipt files are published atomically, captured
output is limited while the child runs to 1 MiB per stream, evidence files to 64 MiB, and malformed
UTF-8 is recorded with replacement characters. Tests cover these boundaries.
A recorded artifact must match a declared output and SHA-256 in the current
passing receipt; the public synthetic script records fresh validation receipts
as artifacts rather than attaching unrelated checked-in example files.
The bounded executor continues enforcing its deadline after stdout/stderr close.
The public synthetic script requires an empty output directory; malformed
hash-consistent event fields and repeated interruption paths are tested.
A local file ledger cannot independently attribute edits made by another
process during the same command, or stop a trusted command from writing outside
its declared outputs; its receipt records the observed file state.

## Prior failure and claim boundary

The preceding `job_9d98cdd61eaf` / `exec_dfb130b64e50` is terminal. Its AC1
verification exited 1 in all three attempts; attempts 2 and 3 also had
rejected `files_touched` claims (`FABRICATION_SUSPECTED`). AC2 and AC4 were
blocked; AC3 passed. Those failures remain historical evidence and are not
relabelled as successes here. This successor does not infer completion from a
green job. The independent claim review is in the separately named
`codbeing_Stage1_독립_QA_및_이력서_판정_20260925.md` under the session's
`02_outputs`. Human30 and Pullim require their own follow-up evidence.
