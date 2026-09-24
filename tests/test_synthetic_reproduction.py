"""The documented public command exercises the complete synthetic path."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "synthetic-cycle"


def test_public_synthetic_command_produces_verified_stage_one_artifacts(tmp_path):
    decisions = json.loads((CASE / "decisions.json").read_text(encoding="utf-8"))
    assert all(item["source_type"] == "direct_decision" for item in decisions)
    output_dir = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "reproduce_synthetic_cycle.sh"), "output"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Stage 1 synthetic artifacts:" in result.stdout
    assert str(output_dir) in result.stdout

    for name in ("model.json", "prediction.json", "comparison.json"):
        produced = json.loads((output_dir / name).read_text(encoding="utf-8"))
        committed = json.loads((CASE / name).read_text(encoding="utf-8"))
        assert produced == committed

    receipt = json.loads((output_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["passed"] is True
    assert all(receipt["checks"].values())
    assert receipt["stage"] == "stage_1_public_reproduction"
    assert receipt["stage_2_future_choice_study"] == "pending"
    assert json.loads((output_dir / "comparison.json").read_text(encoding="utf-8"))["action_match"] is False
