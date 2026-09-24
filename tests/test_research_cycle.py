import json
import subprocess
import sys
from pathlib import Path

import pytest

from codbeing.research_cycle import build_model, compare, predict


CASE = Path(__file__).resolve().parents[1] / "examples" / "synthetic-cycle"


def read(name):
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_public_cycle_matches_committed_artifacts():
    model = build_model(read("decisions.json"))
    card = predict(model, read("scenario.json"), predicted_at="2026-08-01T12:00:00+00:00")
    result = compare(card, read("actual.json"))
    assert model == read("model.json")
    assert card == read("prediction.json")
    assert result == read("comparison.json")
    assert card["evidence_ids"] == ["d1"]
    assert result["action_match"] is False
    assert read("receipt.json")["passed"] is True


def test_rejects_unreviewed_material_and_unmatched_scenario():
    records = read("decisions.json")
    records[0]["source_type"] = "conversation"
    with pytest.raises(ValueError, match="approval"):
        build_model(records)
    model = build_model(read("decisions.json"))
    with pytest.raises(ValueError, match="withheld"):
        predict(model, {"id": "new", "situation": "Other", "conditions": ["unseen"]})


def test_cli_verification_detects_changed_prediction(tmp_path):
    card = read("prediction.json")
    card["action"] = "Changed after the fact"
    changed = tmp_path / "prediction.json"
    changed.write_text(json.dumps(card), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "codbeing.research_cycle", "verify", *(str(CASE / name) for name in ("decisions.json", "scenario.json", "actual.json", "model.json")), str(changed), str(CASE / "comparison.json"), str(tmp_path / "receipt.json")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert json.loads((tmp_path / "receipt.json").read_text())["passed"] is False


def test_supplemental_evidence_requires_detailed_context_meaning_and_approval():
    records = read("decisions.json")
    extra = {
        **records[0],
        "id": "conversation-1",
        "source_type": "conversation",
        "context": "During exam preparation, a friend offered a short volunteer role with a flexible schedule.",
        "meaning": "The speaker was exploring a reversible trial, not committing to the whole role.",
        "review": {"approved_by_user": True, "reviewed_at": "2026-08-02T12:00:00+00:00"},
    }
    for field in ("context", "meaning"):
        incomplete = {**extra, field: "Too little detail"}
        with pytest.raises(ValueError, match=field):
            build_model([*records, incomplete])
    for review in (None, {"approved_by_user": False, "reviewed_at": "2026-08-02T12:00:00+00:00"}):
        with pytest.raises(ValueError, match="approval"):
            build_model([*records, {**extra, "review": review}])
    model = build_model([*records, extra])
    assert model["version"] == "reviewed-evidence-v2"
    assert model["evidence"][-1]["meaning"] == extra["meaning"]
    assert predict(model, read("scenario.json"), predicted_at="2026-08-03T12:00:00+00:00")["model_id"] == model["model_id"]


def test_actual_choice_enters_only_a_later_reviewed_model_build():
    records = read("decisions.json")
    original_model = build_model(records)
    card = predict(original_model, read("scenario.json"), predicted_at="2026-08-01T12:00:00+00:00")
    actual = read("actual.json")
    compare(card, actual)
    assert build_model(records) == original_model
    reviewed_choice = {
        **records[0],
        "id": "actual-1",
        "source_type": "actual_choice",
        "action": actual["action"],
        "reason": actual["reason"],
        "prediction_id": card["prediction_id"],
        "recorded_at": actual["recorded_at"],
    }
    with pytest.raises(ValueError, match="approval"):
        build_model([*records, reviewed_choice])
    reviewed_choice["review"] = {"approved_by_user": True, "reviewed_at": "2026-08-03T12:00:00+00:00"}
    with pytest.raises(ValueError, match="reviewed after"):
        build_model([*records, {**reviewed_choice, "review": {"approved_by_user": True, "reviewed_at": "2026-08-01T12:00:00+00:00"}}])
    next_model = build_model([*records, reviewed_choice])
    assert next_model["model_id"] != original_model["model_id"]
    assert next_model["version"] == "reviewed-evidence-v2"
    assert next_model["evidence"][-1]["prediction_id"] == card["prediction_id"]
    assert card == predict(original_model, read("scenario.json"), predicted_at=card["predicted_at"])


def test_cli_preserves_issued_model_and_prediction_files(tmp_path):
    records = tmp_path / "records.json"
    records.write_text(json.dumps(read("decisions.json")), encoding="utf-8")
    model_path = tmp_path / "model.json"
    scenario_path = CASE / "scenario.json"
    card_path = tmp_path / "prediction.json"

    def run(*args):
        return subprocess.run([sys.executable, "-m", "codbeing.research_cycle", *map(str, args)], capture_output=True, text=True)

    assert run("model", records, model_path).returncode == 0
    assert run("predict", model_path, scenario_path, card_path, "--at", "2026-08-01T12:00:00+00:00").returncode == 0
    original_model = model_path.read_bytes()
    original_card = card_path.read_bytes()
    changed = read("decisions.json")
    changed[0]["action"] = "Different action"
    records.write_text(json.dumps(changed), encoding="utf-8")
    assert run("model", records, model_path).returncode == 2
    assert model_path.read_bytes() == original_model
    assert run("predict", model_path, scenario_path, card_path, "--at", "2026-08-02T12:00:00+00:00").returncode == 2
    assert card_path.read_bytes() == original_card
