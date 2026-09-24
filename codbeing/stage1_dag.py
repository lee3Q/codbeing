"""Reproduce the synthetic A -> B, independent C evidence DAG."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from codbeing.evidence_ledger import EvidenceLedger, LedgerError


def _writer(path: str, value: str) -> list[str]:
    return [sys.executable, "-c", f"from pathlib import Path; Path({path!r}).write_text({value!r})"]


def run_demo(root: Path, *, failure: bool) -> dict:
    if root.exists() and any(root.iterdir()):
        raise LedgerError(f"demo root must be empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "seed.yaml").write_text("goal: synthetic evidence DAG\n")
    (root / "a-input.txt").write_text("v1")
    ledger = EvidenceLedger(root, Path("events.jsonl"))
    ledger.append("seed", path="seed.yaml")
    for ac_id, dependencies in (("A", []), ("B", ["A"]), ("C", [])):
        ledger.append("acceptance_criterion", ac_id=ac_id, text=f"Build {ac_id}",
                      details={"depends_on": dependencies})

    ledger.run("A", _writer("a.txt", "A-v1"), "a-v1-receipt.json",
               inputs=["a-input.txt"], outputs=["a.txt"])
    ledger.append("artifact", ac_id="A", path="a.txt")
    ledger.run("B", _writer("b.txt", "B-v1"), "b-v1-receipt.json",
               inputs=["a.txt"], outputs=["b.txt"])
    ledger.append("artifact", ac_id="B", path="b.txt")
    _, c_receipt = ledger.run("C", _writer("c.txt", "C-v1"), "c-v1-receipt.json",
                              outputs=["c.txt"])
    ledger.append("artifact", ac_id="C", path="c.txt")
    initial = ledger.verify()["current_status"]
    c_identity = {"receipt_id": c_receipt["attempt_id"],
                  "sha256": hashlib.sha256((root / "c.txt").read_bytes()).hexdigest()}

    (root / "a-input.txt").write_text("v2")
    ledger.append("invalidation", ac_id="A", text="A input changed from v1 to v2")
    ledger.append("invalidation", ac_id="B", text="A output invalidates B input")
    pre_rerun = ledger.verify()["current_status"]

    if failure:
        argv = [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(7)"]
    else:
        argv = _writer("a.txt", "A-v2")
    _, a_receipt = ledger.run("A", argv, "a-v2-receipt.json",
                              inputs=["a-input.txt"], outputs=["a.txt"])
    if not failure:
        ledger.append("artifact", ac_id="A", path="a.txt")
        ledger.run("B", _writer("b.txt", "B-v2"), "b-v2-receipt.json",
                   inputs=["a.txt"], outputs=["b.txt"])
        ledger.append("artifact", ac_id="B", path="b.txt")
    state = ledger.verify()
    return {"initial_status": initial, "pre_rerun_status": pre_rerun,
            "current_status": state["current_status"],
            "attempt_counts": {key: len(value["attempts"]) for key, value in state["criteria"].items()},
            "a_receipt": json.loads((root / "a-v2-receipt.json").read_text()),
            "a_receipt_event": a_receipt,
            "c_original": c_identity,
            "c_current": {"receipt_id": state["criteria"]["C"]["attempts"][-1]["attempt_id"],
                          "sha256": hashlib.sha256((root / "c.txt").read_bytes()).hexdigest()},
            "ledger_head": state["head"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=("failure", "success"), required=True)
    args = parser.parse_args(argv)
    result = run_demo(args.root, failure=args.mode == "failure")
    print(json.dumps(result, sort_keys=True))
    return result["a_receipt"]["exit_code"] if args.mode == "failure" else 0


if __name__ == "__main__":
    raise SystemExit(main())
