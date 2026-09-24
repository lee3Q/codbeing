"""Exercise the public synthetic prospective cycle in a fresh journal."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "synthetic-cycle"


def test_fresh_prospective_card_precedes_actual_comparison(tmp_path):
    journal = tmp_path / "prospective"
    assert not journal.exists()

    def run(*args):
        result = subprocess.run(
            [sys.executable, "-m", "codbeing.prospective", *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    card = run("issue", CASE / "decisions.json", CASE / "scenario.json", journal)
    expected_fields = {
        "action", "reason", "pressure_emotion", "alternatives", "confidence",
        "model_version", "evidence_ids", "predicted_at", "prediction_id",
    }
    assert expected_fields <= card.keys()
    assert card["evidence_ids"] == ["d1"]
    assert card["model_version"] == "direct-decision-v1"
    assert run("verify", journal)["status"] == "awaiting_actual"
    assert not (journal / "actual.json").exists()
    assert not (journal / "comparison.json").exists()

    issued_hashes = {
        name: hashlib.sha256((journal / name).read_bytes()).hexdigest()
        for name in ("records.json", "scenario.json", "model.json", "prediction.json")
    }
    comparison = run(
        "record-actual", journal,
        "--action", "Decline the commitment",
        "--reason", "The fictional participant chooses to protect their time",
    )
    assert comparison["prediction_id"] == card["prediction_id"]
    assert comparison["predicted_action"] == card["action"]
    assert comparison["actual_action"] == "Decline the commitment"
    assert comparison["action_match"] is False
    assert run("verify", journal)["status"] == "compared"
    assert json.loads((journal / "prediction.json").read_text()) == card
    assert json.loads((journal / "comparison.json").read_text()) == comparison
    assert issued_hashes == {
        name: hashlib.sha256((journal / name).read_bytes()).hexdigest()
        for name in issued_hashes
    }
    events = [json.loads(line) for line in (journal / "events.jsonl").read_text().splitlines()]
    assert [event["kind"] for event in events] == ["prediction_issued", "actual_recorded"]
    assert events[1]["previous_hash"] == events[0]["event_hash"]
    assert events[0]["recorded_at"] < events[1]["recorded_at"]
