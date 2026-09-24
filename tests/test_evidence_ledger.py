import hashlib
import json
import subprocess
import sys

import pytest

from codbeing.evidence_ledger import EvidenceLedger, LedgerError


def _file(root, name, content):
    path = root / name
    path.write_text(content, encoding="utf-8")
    return path


def _cycle(root):
    _file(root, "seed.yaml", "goal: preserve evidence\n")
    _file(root, "handoff.md", "Completed AC 3\n")
    ledger = EvidenceLedger(root, root / "evidence.jsonl")
    seed = ledger.append("seed", path="seed.yaml")
    criterion = ledger.append("acceptance_criterion", ac_id="3", text="Record hashed lineage")
    command, receipt = ledger.run("3", [sys.executable, "-c",
                                         "from pathlib import Path; Path('artifact.txt').write_text('result\\n'); print('verified')"],
                                  "receipt.json", outputs=["artifact.txt"])
    artifact = ledger.append("artifact", ac_id="3", path="artifact.txt")
    handoff = ledger.append("handoff", ac_id="3", path="handoff.md")
    return ledger, (seed, criterion, command, receipt, artifact, handoff)


def test_replays_complete_hashed_lineage_into_state(tmp_path):
    ledger, events = _cycle(tmp_path)
    seed, criterion, command, receipt, artifact, handoff = events
    assert criterion["source_hash"] == seed["event_hash"]
    assert receipt["command_hash"] == command["event_hash"]
    assert artifact["receipt_hash"] == receipt["event_hash"]
    assert handoff["artifact_hashes"] == [artifact["event_hash"]]
    assert events[0]["file"]["sha256"] == hashlib.sha256((tmp_path / "seed.yaml").read_bytes()).hexdigest()
    state = ledger.verify(expected_head=handoff["event_hash"])
    assert state["head"] == handoff["event_hash"]
    assert state["criteria"]["3"]["status"] == "handed_off"
    assert state["criteria"]["3"]["criterion_hash"] == criterion["event_hash"]


def test_tampering_and_truncation_are_detected(tmp_path):
    ledger, events = _cycle(tmp_path)
    original = ledger.ledger.read_text(encoding="utf-8")
    _file(tmp_path, "artifact.txt", "altered\n")
    assert ledger.verify()["current_status"] == {"3": "INVALID"}
    _file(tmp_path, "artifact.txt", "result\n")
    lines = original.splitlines(keepends=True)
    changed = json.loads(lines[2])
    changed["text"] = "different command"
    lines[2] = json.dumps(changed) + "\n"
    ledger.ledger.write_text("".join(lines), encoding="utf-8")
    with pytest.raises(LedgerError, match="event hash mismatch"):
        ledger.verify()
    ledger.ledger.write_text("".join(original.splitlines(keepends=True)[:-1]), encoding="utf-8")
    with pytest.raises(LedgerError, match="external anchor"):
        ledger.verify(expected_head=events[-1]["event_hash"])


def test_append_rejects_missing_links_and_failed_receipt(tmp_path):
    _file(tmp_path, "seed.yaml", "goal: one\n")
    _file(tmp_path, "artifact.txt", "result\n")
    ledger = EvidenceLedger(tmp_path, tmp_path / "evidence.jsonl")
    ledger.append("seed", path="seed.yaml")
    ledger.append("acceptance_criterion", ac_id="3", text="Evidence")
    with pytest.raises(LedgerError, match="ledger.run"):
        ledger.append("test_receipt", ac_id="3", path="receipt.json", passed=False)
    ledger.run("3", [sys.executable, "-c", "raise SystemExit(1)"], "receipt.json")
    assert ledger.verify()["criteria"]["3"]["status"] == "failed"
    with pytest.raises(LedgerError, match="passing receipt"):
        ledger.append("artifact", ac_id="3", path="artifact.txt")


def test_cli_verifies_state_without_conversation(tmp_path):
    ledger, events = _cycle(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "codbeing.evidence_ledger", "evidence.jsonl", "--root", str(tmp_path), "verify", "--expected-head", events[-1]["event_hash"]],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["criteria"]["3"]["status"] == "handed_off"
    assert ledger.verify()["head"] == events[-1]["event_hash"]
