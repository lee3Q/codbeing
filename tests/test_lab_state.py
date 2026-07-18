"""Focused coverage for local codbeing research-state snapshots."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from codbeing.__main__ import main
from codbeing.lab_state import (
    append_submitted_material,
    load_research_state,
    summarize_research_state,
)


TRACE = {
    "context": "Choose a study plan.",
    "options": ["Plan A", "Plan B"],
    "chosen_action": "Plan A",
    "rejected_options": ["Plan B"],
    "judgment_basis": "Protect focused study time.",
    "observed_behavior": "Compared schedules for two days.",
    "outcome": "Deferred the decision.",
    "aftertaste": "Still uncertain.",
    "memory_confidence": "medium",
    "source": "sanitized local note",
}


def test_missing_local_state_has_a_usable_empty_summary() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        workspace = Path(temporary_directory)
        state = load_research_state(
            workspace / "private-traces" / "decision-traces.json",
            workspace / "private-reports",
        )

    summary = summarize_research_state(state)

    assert state.trace_count == 0
    assert state.latest_report is None
    assert state.trace_store_has_issue is False
    assert summary.evidence == "no submitted DecisionTraces yet"
    assert summary.analysis == "no local reports yet"
    assert summary.apparatus == ("Evidence",)
    assert summary.warnings == ()


def test_json_lab_state_uses_only_codbeing_home_captures(capsys) -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        workspace = Path(temporary_directory)
        home = workspace / "isolated-state"
        private_captures = workspace / "private-traces"
        private_captures.mkdir()
        (private_captures / "ignored.jsonl").write_text('{"note":"ignored"}\n', encoding="utf-8")

        with patch.dict(os.environ, {"CODBEING_HOME": str(home)}, clear=False):
            assert main(["--lab-state", "--json"]) == 0
            assert capsys.readouterr().out == '{"state":"empty_lab"}\n'

            captures = home / "captures"
            captures.mkdir(parents=True)
            (captures / "one.jsonl").write_text('{"note":"x"}\n', encoding="utf-8")

            assert main(["--lab-state", "--json"]) == 0

    assert capsys.readouterr().out == '{"state":"trace_evidence"}\n'


def test_populated_state_summarizes_evidence_reports_and_apparatus() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        workspace = Path(temporary_directory)
        trace_store = workspace / "private-traces" / "decision-traces.json"
        trace_store.parent.mkdir()
        trace_store.write_text(json.dumps([TRACE, TRACE]), encoding="utf-8")
        reports_dir = workspace / "private-reports"
        reports_dir.mkdir()
        older_report = reports_dir / "older.md"
        older_report.write_text("# Older", encoding="utf-8")
        latest_report = reports_dir / "latest.md"
        latest_report.write_text("# Latest", encoding="utf-8")
        os.utime(older_report, (1, 1))
        os.utime(latest_report, (2, 2))

        state = load_research_state(trace_store, reports_dir)

    summary = summarize_research_state(state)

    assert state.trace_count == 2
    assert state.latest_report is not None
    assert state.latest_report.name == "latest.md"
    assert state.reports == (state.latest_report, Path(state.latest_report.parent / "older.md"))
    assert summary.evidence == "2 stored DecisionTraces"
    assert summary.analysis == "latest local report is latest.md"
    assert summary.apparatus == ("Evidence", "Self Code", "Simulation", "Analysis")


def test_partial_trace_store_keeps_valid_evidence_and_warns() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        workspace = Path(temporary_directory)
        trace_store = workspace / "private-traces" / "decision-traces.json"
        trace_store.parent.mkdir()
        trace_store.write_text(
            json.dumps([TRACE, {"context": "Incomplete local evidence."}]),
            encoding="utf-8",
        )

        state = load_research_state(trace_store, workspace / "private-reports")

    summary = summarize_research_state(state)

    assert state.trace_count == 1
    assert state.traces[0]["context"] == TRACE["context"]
    assert state.trace_store_has_issue is True
    assert summary.evidence == "local DecisionTrace store needs repair before it can be fully read."
    assert summary.warnings == ("Some saved DecisionTrace evidence could not be read.",)


def test_malformed_trace_store_and_report_path_do_not_crash_loading() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        workspace = Path(temporary_directory)
        trace_store = workspace / "private-traces" / "decision-traces.json"
        trace_store.parent.mkdir()
        trace_store.write_text("{not json", encoding="utf-8")
        reports_path = workspace / "private-reports"
        reports_path.write_text("not a directory", encoding="utf-8")

        state = load_research_state(trace_store, reports_path)

    summary = summarize_research_state(state)

    assert state.trace_count == 0
    assert state.trace_store_has_issue is True
    assert state.reports_directory_has_issue is True
    assert summary.analysis == "no local reports yet"
    assert summary.warnings == (
        "Some saved DecisionTrace evidence could not be read.",
        "Some local report metadata could not be read.",
    )


def test_submitted_material_is_persisted_in_local_research_state() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        workspace = Path(temporary_directory)
        material_store = workspace / "private-traces" / "submitted-material.json"

        assert append_submitted_material(material_store, "I delayed the decision after the conversation.") == 1
        state = load_research_state(
            workspace / "private-traces" / "decision-traces.json",
            workspace / "private-reports",
            material_store,
        )

    assert state.submitted_material == ("I delayed the decision after the conversation.",)
    assert state.submitted_material_count == 1
    assert state.submitted_material_store_has_issue is False
