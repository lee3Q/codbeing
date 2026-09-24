"""Positive assertions for both subprocess-backed DAG reproduction paths."""

import hashlib
import json
import subprocess
import sys
import pytest

from codbeing.evidence_ledger import EvidenceLedger
from codbeing.stage1_dag import run_demo
from codbeing.evidence_ledger import LedgerError


def test_demo_preserves_nonempty_root(tmp_path):
    root = tmp_path / "existing"
    root.mkdir()
    (root / "seed.yaml").write_text("user content")
    with pytest.raises(LedgerError, match="demo root must be empty"):
        run_demo(root, failure=False)
    assert (root / "seed.yaml").read_text() == "user content"


def _run(tmp_path, mode):
    root = tmp_path / mode
    result = subprocess.run(
        [sys.executable, "-m", "codbeing.stage1_dag", "--root", str(root), "--mode", mode],
        capture_output=True, text=True,
    )
    return root, result, json.loads(result.stdout)


def _shared_assertions(root, payload):
    assert payload["initial_status"] == {"A": "PASS", "B": "PASS", "C": "PASS"}
    assert payload["pre_rerun_status"] == {"A": "INVALID", "B": "INVALID", "C": "PASS"}
    assert payload["c_current"] == payload["c_original"]
    assert payload["c_original"]["sha256"] == hashlib.sha256((root / "c.txt").read_bytes()).hexdigest()
    ledger = EvidenceLedger(root, root / "events.jsonl")
    state = ledger.verify(expected_head=payload["ledger_head"])
    assert state["current_status"] == payload["current_status"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert [event["ac_id"] for event in events if event["kind"] == "invalidation"] == ["A", "B"]
    assert [event["ac_id"] for event in events if event["kind"] == "command"] == ["A", "B", "C"] + (
        ["A", "B"] if payload["current_status"]["A"] == "PASS" else ["A"])
    return state


def test_failure_dag_cli_exits_seven_and_blocks_b_without_rerun(tmp_path):
    root, process, payload = _run(tmp_path, "failure")
    assert process.returncode == 7, process.stderr
    assert process.stderr == ""
    assert payload["current_status"] == {"A": "FAIL", "B": "BLOCKED", "C": "PASS"}
    assert payload["attempt_counts"] == {"A": 2, "B": 1, "C": 1}
    receipt = payload["a_receipt"]
    assert receipt["exit_code"] == payload["a_receipt_event"]["exit_code"] == 7
    assert receipt["stdout"] == payload["a_receipt_event"]["stdout"] == ""
    assert receipt["stderr"] == payload["a_receipt_event"]["stderr"] == "boom\n"
    assert receipt["outputs"] == {"a.txt": None}
    assert receipt["attempt_id"] == payload["a_receipt_event"]["attempt_id"]
    assert receipt["command_hash"] == payload["a_receipt_event"]["command_hash"]
    assert payload["a_receipt_event"]["passed"] is False
    assert (root / "a.txt").read_text() == "A-v1"
    assert not (root / "b-v2-receipt.json").exists()
    state = _shared_assertions(root, payload)
    assert state["criteria"]["B"]["depends_on"] == ["A"]


def test_success_dag_reruns_only_a_and_b(tmp_path):
    root, process, payload = _run(tmp_path, "success")
    assert process.returncode == 0, process.stderr
    assert payload["current_status"] == {"A": "PASS", "B": "PASS", "C": "PASS"}
    assert payload["attempt_counts"] == {"A": 2, "B": 2, "C": 1}
    assert payload["a_receipt"]["exit_code"] == 0
    assert payload["a_receipt_event"]["passed"] is True
    assert (root / "a.txt").read_text() == "A-v2"
    assert (root / "b.txt").read_text() == "B-v2"
    assert (root / "b-v2-receipt.json").is_file()
    _shared_assertions(root, payload)
