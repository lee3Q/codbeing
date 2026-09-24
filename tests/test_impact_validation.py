import json
import sys

import pytest

from codbeing.impact_validation import GraphError, ImpactValidation


def _node(ident, deps=()):
    script = (
        "from pathlib import Path; "
        f"counter=Path('{ident}.count'); "
        "n=int(counter.read_text())+1 if counter.exists() else 1; "
        "counter.write_text(str(n)); "
        f"Path('{ident}.out').write_text(str(n))"
    )
    return {
        "id": ident,
        "depends_on": list(deps),
        "inputs": [f"{ident}.input"],
        "artifacts": [f"{ident}.out"],
        "command": [sys.executable, "-c", script],
    }


def _graph(tmp_path):
    for ident in ("a", "b", "c"):
        (tmp_path / f"{ident}.input").write_text("original")
    return ImpactValidation(tmp_path, {"nodes": [_node("b", ("a",)), _node("c"), _node("a")]})


def test_only_affected_downstream_nodes_rerun(tmp_path):
    graph = _graph(tmp_path)
    assert not any(item["complete"] for item in graph.status().values())
    assert all(item["complete"] for item in graph.run().values())
    graph.run()
    assert [(tmp_path / f"{ident}.count").read_text() for ident in ("a", "b", "c")] == ["1", "1", "1"]

    (tmp_path / "a.input").write_text("changed")
    status = graph.status()
    assert [ident for ident, item in status.items() if not item["complete"]] == ["a", "b"]
    assert all(item["complete"] for item in graph.run().values())
    assert [(tmp_path / f"{ident}.count").read_text() for ident in ("a", "b", "c")] == ["2", "2", "1"]


def test_completion_requires_current_artifacts_and_receipts_not_claim(tmp_path):
    graph = _graph(tmp_path)
    graph.run()
    (tmp_path / "a.out").write_text("tampered")
    assert not graph.status()["a"]["complete"]
    assert not graph.status()["b"]["complete"]
    assert graph.status()["c"]["complete"]
    graph.run()
    receipt_path = tmp_path / ".codbeing-validation" / "b.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["exit_code"] = 1
    receipt_path.write_text(json.dumps(receipt))
    assert not graph.status()["b"]["complete"]
    assert graph.status()["a"]["complete"]


def test_rejects_cycles_and_missing_production(tmp_path):
    with pytest.raises(GraphError, match="dependency cycle"):
        ImpactValidation(tmp_path, {"nodes": [_node("a", ("b",)), _node("b", ("a",))]})
    (tmp_path / "a.input").write_text("ready")
    node = _node("a")
    node["command"] = [sys.executable, "-c", "pass"]
    graph = ImpactValidation(tmp_path, {"nodes": [node]})
    with pytest.raises(GraphError, match="did not produce"):
        graph.run()
    assert not graph.status()["a"]["complete"]
