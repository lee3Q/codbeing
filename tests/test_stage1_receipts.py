"""Stage 1 subprocess receipts and current evidence status."""

import hashlib
import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from codbeing.evidence_ledger import EvidenceLedger, LedgerError, MAX_CAPTURE_BYTES, MAX_EVIDENCE_BYTES, _hash


def _ledger(tmp_path):
    (tmp_path / "seed.yaml").write_text("goal: receipts\n")
    ledger = EvidenceLedger(tmp_path, tmp_path / "events.jsonl")
    ledger.append("seed", path="seed.yaml")
    ledger.append("acceptance_criterion", ac_id="A", text="Verify subprocess evidence")
    return ledger


def test_success_receipt_binds_command_attempt_and_artifact_hashes(tmp_path):
    ledger = _ledger(tmp_path)
    source = tmp_path / "input.txt"
    source.write_text("v1")
    argv = [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('done'); print('ok')"]
    command, event = ledger.run("A", argv, "receipt.json", inputs=["input.txt"], outputs=["out.txt"])
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert event["passed"] is True
    assert receipt["argv"] == argv
    assert receipt["command_hash"] == command["event_hash"]
    assert receipt["attempt_id"] == command["attempt_id"] == event["attempt_id"]
    assert receipt["exit_code"] == 0
    assert receipt["stdout"] == "ok\n" and receipt["stderr"] == ""
    assert receipt["inputs"] == {"input.txt": hashlib.sha256(b"v1").hexdigest()}
    assert receipt["outputs"] == {"out.txt": hashlib.sha256(b"done").hexdigest()}
    assert ledger.verify()["current_status"] == {"A": "PASS"}
    (tmp_path / "out.txt").write_text("tampered")
    assert ledger.verify()["current_status"] == {"A": "INVALID"}
    (tmp_path / "out.txt").write_text("done")
    source.write_text("v2")
    assert ledger.verify()["current_status"] == {"A": "INVALID"}
    (tmp_path / "out.txt").unlink()
    assert ledger.verify()["current_status"] == {"A": "INVALID"}


def test_failed_command_and_missing_output_never_pass(tmp_path):
    ledger = _ledger(tmp_path)
    _, event = ledger.run("A", [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(7)"], "failure.json")
    receipt = json.loads((tmp_path / "failure.json").read_text())
    assert event["passed"] is False
    assert (receipt["exit_code"], receipt["stdout"], receipt["stderr"]) == (7, "", "boom\n")
    assert ledger.verify()["current_status"] == {"A": "FAIL"}
    _, missing = ledger.run("A", [sys.executable, "-c", "pass"], "missing.json", outputs=["absent.txt"])
    assert missing["passed"] is False
    assert ledger.verify()["current_status"] == {"A": "FAIL"}
    assert len(ledger.verify()["criteria"]["A"]["attempts"]) == 2


def test_preexisting_output_cannot_satisfy_new_attempt(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.run("A", [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('old')"],
               "first.json", outputs=["out.txt"])
    assert ledger.verify()["current_status"] == {"A": "PASS"}
    _, event = ledger.run("A", [sys.executable, "-c", "pass"], "stale.json", outputs=["out.txt"])
    assert event["passed"] is False
    assert json.loads((tmp_path / "stale.json").read_text())["outputs"] == {"out.txt": None}
    assert ledger.verify()["current_status"] == {"A": "FAIL"}
    assert len(ledger.verify()["criteria"]["A"]["attempts"]) == 2


def test_run_rejects_nonrelative_receipt_and_input_output_alias(tmp_path):
    ledger = _ledger(tmp_path)
    (tmp_path / "same.txt").write_text("source")
    with pytest.raises(LedgerError, match="workspace-relative"):
        ledger.run("A", [sys.executable, "-c", "pass"], str(tmp_path / "receipt.json"))
    with pytest.raises(LedgerError, match="also be an input"):
        ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json",
                   inputs=["same.txt"], outputs=["same.txt"])
    assert not ledger.ledger.read_text().count('"kind":"command"')


def test_timeout_and_interruption_keep_attempts(tmp_path):
    ledger = _ledger(tmp_path)
    _, timeout = ledger.run("A", [sys.executable, "-c", "import time; time.sleep(1)"], "timeout.json", timeout=0.01)
    assert timeout["passed"] is False
    assert json.loads((tmp_path / "timeout.json").read_text())["outcome"] == "timeout"
    with patch("codbeing.evidence_ledger._execute_bounded", return_value=(130, "", "interrupted", "interrupted")):
        _, interrupted = ledger.run("A", [sys.executable, "-c", "pass"], "interrupted.json")
    assert interrupted["passed"] is False
    attempts = ledger.verify()["criteria"]["A"]["attempts"]
    assert [attempt["outcome"] for attempt in attempts] == ["timeout", "interrupted"]
    assert ledger.verify()["current_status"] == {"A": "FAIL"}


def test_invalidation_and_receipt_tamper(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json")
    ledger.append("invalidation", ac_id="A", text="input changed")
    assert ledger.verify()["current_status"] == {"A": "INVALID"}
    receipt_path = tmp_path / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["exit_code"] = 0
    receipt["stdout"] = "forged"
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(LedgerError, match="evidence file changed"):
        ledger.verify()


def test_handoff_cannot_restore_pass_after_invalidation(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.run("A", [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('old')"],
               "receipt.json", outputs=["out.txt"])
    ledger.append("artifact", ac_id="A", path="out.txt")
    ledger.append("invalidation", ac_id="A", text="inputs changed")
    (tmp_path / "handoff.md").write_text("old handoff")
    with pytest.raises(LedgerError, match="missing artifact links"):
        ledger.append("handoff", ac_id="A", path="handoff.md")
    assert ledger.verify()["current_status"] == {"A": "INVALID"}


def test_public_append_cannot_forge_observed_pass(tmp_path):
    ledger = _ledger(tmp_path)
    (tmp_path / "forged.json").write_text('{"exit_code":0,"stdout":"","stderr":""}')
    with pytest.raises(TypeError, match="_observed"):
        ledger.append("test_receipt", ac_id="A", path="forged.json", passed=True, _observed=True)
    with pytest.raises(LedgerError, match="observed command provenance"):
        ledger.append("command", ac_id="A", text="pass", details={"attempt_id": "fake", "inputs": {}, "outputs": []})
    assert ledger.verify()["current_status"] == {"A": "PENDING"}


def test_artifact_must_match_declared_output_in_passing_receipt(tmp_path):
    ledger = _ledger(tmp_path)
    (tmp_path / "unrelated.txt").write_text("old")
    ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json")
    with pytest.raises(LedgerError, match="matching declared output"):
        ledger.append("artifact", ac_id="A", path="unrelated.txt")
    assert ledger.verify()["current_status"] == {"A": "PASS"}


@pytest.mark.parametrize("field,value", [("inputs", 4), ("outputs", "out.txt"), ("timeout", 0)])
def test_run_rejects_wrong_argument_types(tmp_path, field, value):
    ledger = _ledger(tmp_path)
    with pytest.raises(LedgerError):
        ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json", **{field: value})
    assert ledger.verify()["current_status"] == {"A": "PENDING"}


def test_untracked_output_is_preserved(tmp_path):
    ledger = _ledger(tmp_path)
    (tmp_path / "out.txt").write_text("user edit")
    with pytest.raises(LedgerError, match="refusing to overwrite"):
        ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json", outputs=["out.txt"])
    assert (tmp_path / "out.txt").read_text() == "user edit"
    assert ledger.verify()["current_status"] == {"A": "PENDING"}


def test_existing_receipt_recovers_without_rerunning_command(tmp_path):
    ledger = _ledger(tmp_path)
    argv = [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('done')"]
    original_append = ledger._append_event

    def interrupt_receipt(kind, **kwargs):
        if kind == "test_receipt":
            raise KeyboardInterrupt
        return original_append(kind, **kwargs)

    with patch.object(ledger, "_append_event", side_effect=interrupt_receipt):
        with pytest.raises(KeyboardInterrupt):
            ledger.run("A", argv, "receipt.json", outputs=["out.txt"])
    assert (tmp_path / "receipt.json").is_file()
    assert ledger.verify()["current_status"] == {"A": "PENDING"}
    with patch("codbeing.evidence_ledger._execute_bounded", side_effect=AssertionError("reran")):
        command, event = ledger.run("A", argv, "receipt.json", outputs=["out.txt"])
    assert event["passed"] is True
    assert event["command_hash"] == command["event_hash"]
    assert ledger.verify()["current_status"] == {"A": "PASS"}
    assert len(ledger.verify()["criteria"]["A"]["attempts"]) == 1


def test_default_timeout_is_bounded(tmp_path):
    ledger = _ledger(tmp_path)
    with patch("codbeing.evidence_ledger._execute_bounded", return_value=(124, "", "", "timeout")) as proc:
        _, event = ledger.run("A", [sys.executable, "-c", "pass"], "timeout.json")
    assert proc.call_args.args[2] == 300.0
    assert event["passed"] is False
    assert json.loads((tmp_path / "timeout.json").read_text())["outcome"] == "timeout"


def test_closed_stream_child_still_times_out(tmp_path):
    ledger = _ledger(tmp_path)
    argv = [sys.executable, "-c", "import os,time; os.close(1); os.close(2); time.sleep(2)"]
    _, event = ledger.run("A", argv, "receipt.json", timeout=0.05)
    assert event["passed"] is False
    assert json.loads((tmp_path / "receipt.json").read_text())["outcome"] == "timeout"


def test_unknown_command_outcome_blocks_retry_without_receipt(tmp_path):
    ledger = _ledger(tmp_path)
    argv = [sys.executable, "-c", "pass"]
    with patch("codbeing.evidence_ledger._execute_bounded", side_effect=SystemExit(9)):
        with pytest.raises(SystemExit):
            ledger.run("A", argv, "receipt.json")
    assert not (tmp_path / "receipt.json").exists()
    assert ledger.verify()["current_status"] == {"A": "PENDING"}
    with patch("codbeing.evidence_ledger._execute_bounded", side_effect=AssertionError("reran")):
        with pytest.raises(LedgerError, match="unknown execution outcome"):
            ledger.run("A", argv, "retry.json")


@pytest.mark.parametrize("bad_timeout", [float("inf"), float("nan"), 3601])
def test_run_rejects_unbounded_timeout(tmp_path, bad_timeout):
    ledger = _ledger(tmp_path)
    with pytest.raises(LedgerError, match="timeout must be finite"):
        ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json", timeout=bad_timeout)


def test_invalid_incomplete_receipt_is_reported_without_rerun(tmp_path):
    ledger = _ledger(tmp_path)
    argv = [sys.executable, "-c", "pass"]
    original_append = ledger._append_event

    def interrupt_receipt(kind, **kwargs):
        if kind == "test_receipt":
            raise KeyboardInterrupt
        return original_append(kind, **kwargs)

    with patch.object(ledger, "_append_event", side_effect=interrupt_receipt):
        with pytest.raises(KeyboardInterrupt):
            ledger.run("A", argv, "receipt.json")
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("{bad")
    with patch("codbeing.evidence_ledger._execute_bounded", side_effect=AssertionError("reran")):
        with pytest.raises(LedgerError, match="invalid incomplete receipt JSON"):
            ledger.run("A", argv, "receipt.json")
    receipt_path.write_text(json.dumps({"outputs": []}))
    with pytest.raises(LedgerError, match="incomplete receipt does not match"):
        ledger.run("A", argv, "receipt.json")


def test_non_utf8_output_is_recorded_without_decode_crash(tmp_path):
    ledger = _ledger(tmp_path)
    _, event = ledger.run("A", [sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([255]))"],
                          "receipt.json")
    assert event["passed"] is True
    assert json.loads((tmp_path / "receipt.json").read_text())["stdout"] == "\ufffd"


def test_oversized_input_and_output_fail_closed(tmp_path):
    ledger = _ledger(tmp_path)
    (tmp_path / "large-input.bin").write_bytes(b"")
    with (tmp_path / "large-input.bin").open("r+b") as stream:
        stream.truncate(MAX_EVIDENCE_BYTES + 1)
    with pytest.raises(LedgerError, match="artifact exceeds size limit"):
        ledger.run("A", [sys.executable, "-c", "pass"], "input.json", inputs=["large-input.bin"])
    command = [sys.executable, "-c", f"from pathlib import Path; Path('big.bin').open('wb').truncate({MAX_EVIDENCE_BYTES + 1})"]
    _, event = ledger.run("A", command, "output.json", outputs=["big.bin"])
    assert event["passed"] is False
    assert json.loads((tmp_path / "output.json").read_text())["outcome"] == "output_limit"


def test_oversized_stdout_fails_with_bounded_receipt(tmp_path):
    ledger = _ledger(tmp_path)
    command = [sys.executable, "-c", f"import sys; sys.stdout.buffer.write(b'x' * {MAX_CAPTURE_BYTES + 1})"]
    _, event = ledger.run("A", command, "receipt.json")
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert event["passed"] is False
    assert receipt["outcome"] == "output_limit"
    assert len(receipt["stdout"]) == MAX_CAPTURE_BYTES


def test_partial_receipt_write_never_exposes_target(tmp_path):
    ledger = _ledger(tmp_path)
    with patch("codbeing.evidence_ledger.json.dump", side_effect=OSError("disk interrupted")):
        with pytest.raises(OSError, match="disk interrupted"):
            ledger.run("A", [sys.executable, "-c", "pass"], "receipt.json")
    assert not (tmp_path / "receipt.json").exists()
    assert not list(tmp_path.glob(".receipt-*"))
    with pytest.raises(LedgerError, match="unknown execution outcome"):
        ledger.run("A", [sys.executable, "-c", "pass"], "retry.json")


def test_repeated_interruptions_reconcile_without_duplicate_execution(tmp_path):
    ledger = _ledger(tmp_path)
    argv = [sys.executable, "-c", "pass"]
    with patch("codbeing.evidence_ledger._execute_bounded", side_effect=SystemExit(9)):
        with pytest.raises(SystemExit):
            ledger.run("A", argv, "first.json")
    ledger.append("invalidation", ac_id="A", text="manual reconciliation: outcome unknown")
    original_append = ledger._append_event

    def interrupt_receipt(kind, **kwargs):
        if kind == "test_receipt":
            raise KeyboardInterrupt
        return original_append(kind, **kwargs)

    with patch.object(ledger, "_append_event", side_effect=interrupt_receipt):
        with pytest.raises(KeyboardInterrupt):
            ledger.run("A", argv, "second.json")
    with patch("codbeing.evidence_ledger._execute_bounded", side_effect=AssertionError("reran")):
        _, receipt_event = ledger.run("A", argv, "second.json")
    assert receipt_event["passed"] is True
    assert ledger.verify()["current_status"] == {"A": "PASS"}
    assert len(ledger.verify()["criteria"]["A"]["attempts"]) == 1


@pytest.mark.parametrize("field,value", [("kind", []), ("ac_id", [])])
def test_hash_consistent_malformed_event_fails_cleanly(tmp_path, field, value):
    ledger = _ledger(tmp_path)
    state = ledger.verify()
    event = {"sequence": 3, "previous_hash": state["head"], "kind": "command",
             "recorded_at": "2026-01-01T00:00:00+00:00", "ac_id": "A",
             "criterion_hash": state["criteria"]["A"]["criterion_hash"], "text": "pass"}
    event[field] = value
    event["event_hash"] = _hash(event)
    with ledger.ledger.open("a") as stream:
        stream.write(json.dumps(event, separators=(",", ":")) + "\n")
    with pytest.raises(LedgerError):
        ledger.verify()


def test_run_cli_returns_observed_failure_code(tmp_path):
    ledger = _ledger(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "codbeing.evidence_ledger", "events.jsonl", "--root", str(tmp_path),
         "run", "--ac-id", "A", "--receipt", "cli-failure.json", "--", sys.executable,
         "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(7)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 7
    assert json.loads(result.stdout)["receipt"]["passed"] is False
    assert json.loads((tmp_path / "cli-failure.json").read_text())["stderr"] == "boom\n"
    assert ledger.verify()["current_status"] == {"A": "FAIL"}


def test_rerun_preserves_old_artifact_event_when_output_changes(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.run("A", [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('v1')"],
               "v1.json", outputs=["out.txt"])
    first_artifact = ledger.append("artifact", ac_id="A", path="out.txt")
    (tmp_path / "out.txt").write_text("changed")
    assert ledger.verify()["current_status"] == {"A": "INVALID"}
    ledger.append("invalidation", ac_id="A", text="new version")
    with pytest.raises(LedgerError, match="refusing to overwrite"):
        ledger.run("A", [sys.executable, "-c", "pass"], "blocked.json", outputs=["out.txt"])
    assert (tmp_path / "out.txt").read_text() == "changed"
    (tmp_path / "out.txt").unlink()
    ledger.run("A", [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('v2')"],
               "v2.json", outputs=["out.txt"])
    state = ledger.verify()
    assert state["current_status"] == {"A": "PASS"}
    assert first_artifact["event_hash"] in ledger.ledger.read_text()
    assert len(state["criteria"]["A"]["attempts"]) == 2
