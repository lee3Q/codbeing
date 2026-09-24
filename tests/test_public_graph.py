"""Change real synthetic inputs and prove selective, immutable-aware reruns."""

import json
import shutil
from pathlib import Path

from codbeing.impact_validation import ImpactValidation


ROOT = Path(__file__).resolve().parents[1]


def test_public_graph_regenerates_only_affected_descendants(tmp_path):
    for source in (ROOT / "codbeing" / "__init__.py", ROOT / "codbeing" / "research_cycle.py"):
        target = tmp_path / "codbeing" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    case = tmp_path / "examples" / "synthetic-cycle"
    case.mkdir(parents=True)
    for name in ("decisions.json", "scenario.json", "actual.json", "model.json",
                 "prediction.json", "comparison.json", "receipt.json", "validation-graph.json"):
        shutil.copy2(ROOT / "examples" / "synthetic-cycle" / name, case / name)

    graph = ImpactValidation(tmp_path, json.loads((case / "validation-graph.json").read_text()))
    assert all(item["complete"] for item in graph.run().values())
    def run_ids():
        return {ident: json.loads((tmp_path / ".codbeing-validation" / f"{ident}.json").read_text())["run_id"]
                for ident in graph.order}
    before = run_ids()
    scenario = json.loads((case / "scenario.json").read_text())
    scenario["situation"] = "The same project asks for help under a revised fictional description."
    (case / "scenario.json").write_text(json.dumps(scenario))
    assert [ident for ident, item in graph.status().items() if not item["complete"]] == ["prediction", "comparison", "verification"]
    assert all(item["complete"] for item in graph.run().values())
    after_scenario = run_ids()
    assert after_scenario["model"] == before["model"]
    assert all(after_scenario[ident] != before[ident] for ident in ("prediction", "comparison", "verification"))

    original_model = (case / "model.json").read_bytes()
    decisions = json.loads((case / "decisions.json").read_text())
    decisions[0]["action"] = "Decline the trial and protect study time"
    (case / "decisions.json").write_text(json.dumps(decisions))
    assert not any(item["complete"] for item in graph.status().values())
    assert all(item["complete"] for item in graph.run().values())
    assert (case / "model.json").read_bytes() != original_model
    history = tmp_path / ".codbeing-validation" / "history" / "model"
    assert any(path.read_bytes() == original_model for path in history.rglob("model.json"))
