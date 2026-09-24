"""Create and assert fresh, synthetic Stage 1 review evidence.

The failure DAG CLI is invoked here as a subject under test. This script is
the positive verification command: it exits zero only when the failure path
and the independent success and prospective paths meet their contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codbeing.evidence_ledger import _execute_bounded

CASE = ROOT / "examples" / "synthetic-cycle"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, "-m", *args]
    code, stdout, stderr, _ = _execute_bounded(argv, ROOT, 120)
    return subprocess.CompletedProcess(argv, code, stdout, stderr)


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_saved(out: Path) -> dict:
    """Recheck a named result without changing its evidence files."""
    summary = json.loads((out / "review-summary.json").read_text())
    for mode, status, counts in (
        ("failure", {"A": "FAIL", "B": "BLOCKED", "C": "PASS"}, {"A": 2, "B": 1, "C": 1}),
        ("success", {"A": "PASS", "B": "PASS", "C": "PASS"}, {"A": 2, "B": 2, "C": 1}),
    ):
        result = json.loads((out / f"{mode}-result.json").read_text())
        replay = _run("codbeing.evidence_ledger", "events.jsonl", "--root", str(out / mode),
                      "verify", "--expected-head", result["ledger_head"])
        assert replay.returncode == 0, replay.stderr
        state = json.loads(replay.stdout)
        assert result["current_status"] == state["current_status"] == status
        assert result["attempt_counts"] == counts
        assert result["c_original"] == result["c_current"]
        assert result["c_original"]["sha256"] == _sha(out / mode / "c.txt")
        assert summary["dag"][mode]["ledger_sha256"] == _sha(out / mode / "events.jsonl")
        assert (out / mode / "a-input.txt").read_text() == "v2"
        if mode == "failure":
            receipt = json.loads((out / mode / "a-v2-receipt.json").read_text())
            assert (receipt["exit_code"], receipt["stdout"], receipt["stderr"]) == (7, "", "boom\n")
            assert receipt["outputs"] == {"a.txt": None}
            assert not (out / mode / "b-v2-receipt.json").exists()
        else:
            assert (out / mode / "b-v2-receipt.json").is_file()
    prospective = json.loads((out / "prospective-result.json").read_text())
    check = _run("codbeing.prospective", "verify", str(out / "prospective"),
                 "--expected-head", prospective["compared"]["head"])
    assert check.returncode == 0 and json.loads(check.stdout)["status"] == "compared"
    assert prospective["prediction_sha256"] == _sha(out / "prospective" / "prediction.json")
    assert prospective["comparison"]["action_match"] is False
    return summary


def verify_review(out: Path) -> dict:
    if out.exists():
        return verify_saved(out)
    out.mkdir(parents=True, exist_ok=False)
    dag = {}
    for mode, code, status, attempts in (
        ("failure", 7, {"A": "FAIL", "B": "BLOCKED", "C": "PASS"}, {"A": 2, "B": 1, "C": 1}),
        ("success", 0, {"A": "PASS", "B": "PASS", "C": "PASS"}, {"A": 2, "B": 2, "C": 1}),
    ):
        process = _run("codbeing.stage1_dag", "--root", str(out / mode), "--mode", mode)
        assert process.returncode == code, (mode, process.stderr)
        assert process.stderr == ""
        result = json.loads(process.stdout)
        assert result["initial_status"] == {"A": "PASS", "B": "PASS", "C": "PASS"}
        assert result["pre_rerun_status"] == {"A": "INVALID", "B": "INVALID", "C": "PASS"}
        assert result["current_status"] == status
        assert result["attempt_counts"] == attempts
        assert result["c_original"] == result["c_current"]
        assert result["c_original"]["sha256"] == _sha(out / mode / "c.txt")
        assert (out / mode / "a-input.txt").read_text() == "v2"
        assert (out / mode / "events.jsonl").is_file()
        replay = _run("codbeing.evidence_ledger", "events.jsonl", "--root", str(out / mode),
                      "verify", "--expected-head", result["ledger_head"])
        assert replay.returncode == 0, replay.stderr
        replayed = json.loads(replay.stdout)
        assert replayed["current_status"] == status
        assert {ac: len(replayed["criteria"][ac]["attempts"]) for ac in attempts} == attempts
        events = [json.loads(line) for line in (out / mode / "events.jsonl").read_text().splitlines()]
        assert [event["kind"] for event in events if event["kind"] == "invalidation"] == ["invalidation"] * 2
        assert [event["ac_id"] for event in events if event["kind"] == "invalidation"] == ["A", "B"]
        assert [event["ac_id"] for event in events if event["kind"] == "command"] == (
            ["A", "B", "C", "A"] if mode == "failure" else ["A", "B", "C", "A", "B"])
        if mode == "failure":
            receipt = result["a_receipt"]
            assert (receipt["exit_code"], receipt["stdout"], receipt["stderr"]) == (7, "", "boom\n")
            assert receipt["outcome"] == "exited" and receipt["outputs"] == {"a.txt": None}
            assert receipt["attempt_id"] == result["a_receipt_event"]["attempt_id"]
            assert receipt["command_hash"] == result["a_receipt_event"]["command_hash"]
            assert result["a_receipt_event"]["passed"] is False
            assert not (out / mode / "b-v2-receipt.json").exists()
        else:
            assert result["a_receipt"]["exit_code"] == 0
            assert (out / mode / "b-v2-receipt.json").is_file()
        _json(out / f"{mode}-result.json", result)
        dag[mode] = {"cli_exit_code": process.returncode, "ledger_head": result["ledger_head"],
                     "ledger_sha256": _sha(out / mode / "events.jsonl"), "status": status,
                     "c_receipt_id": result["c_original"]["receipt_id"],
                     "c_sha256": result["c_original"]["sha256"]}

    journal = out / "prospective"
    issue = _run("codbeing.prospective", "issue", str(CASE / "decisions.json"),
                 str(CASE / "scenario.json"), str(journal))
    assert issue.returncode == 0, issue.stderr
    card = json.loads(issue.stdout)
    assert {"action", "reason", "pressure_emotion", "alternatives", "confidence",
            "model_version", "evidence_ids", "predicted_at"} <= card.keys()
    awaiting = _run("codbeing.prospective", "verify", str(journal))
    assert awaiting.returncode == 0 and json.loads(awaiting.stdout)["status"] == "awaiting_actual"
    original_card_sha = _sha(journal / "prediction.json")
    actual = _run("codbeing.prospective", "record-actual", str(journal),
                  "--action", "Decline the commitment", "--reason",
                  "The fictional participant chooses to protect their time")
    assert actual.returncode == 0, actual.stderr
    comparison = json.loads(actual.stdout)
    assert comparison["prediction_id"] == card["prediction_id"]
    assert comparison["actual_action"] == "Decline the commitment"
    assert comparison["action_match"] is False
    compared = _run("codbeing.prospective", "verify", str(journal))
    assert compared.returncode == 0 and json.loads(compared.stdout)["status"] == "compared"
    assert _sha(journal / "prediction.json") == original_card_sha
    _json(out / "prospective-result.json", {"card": card, "comparison": comparison,
                                              "awaiting": json.loads(awaiting.stdout),
                                              "compared": json.loads(compared.stdout),
                                              "prediction_sha256": original_card_sha})
    summary = {"dag": dag, "prospective": {"prediction_id": card["prediction_id"],
               "prediction_sha256": original_card_sha, "status": "compared"}}
    _json(out / "review-summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_review(args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
