"""Prospective publication and later comparison use a real append-only order."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from codbeing.prospective import ProspectiveJournal, main


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "synthetic-cycle"


def inputs():
    return (json.loads((CASE / "decisions.json").read_text()),
            json.loads((CASE / "scenario.json").read_text()))


def test_issued_prediction_precedes_later_choice_and_can_be_replayed(tmp_path):
    first = datetime(2026, 9, 24, 1, 0, tzinfo=timezone.utc)
    times = iter((first, first + timedelta(seconds=1)))
    journal = ProspectiveJournal(tmp_path / "journal", now=lambda: next(times))
    card = journal.issue(*inputs())
    issued = journal.verify()
    assert issued["status"] == "awaiting_actual"
    assert card["predicted_at"] == first.isoformat()
    result = journal.record_actual("Try a two-week limited commitment", "A short trial is manageable")
    compared = journal.verify()
    assert result["action_match"] is True
    assert compared["status"] == "compared"
    assert compared["head"] != issued["head"]
    assert journal.verify(expected_head=compared["head"]) == compared
    with pytest.raises(ValueError, match="already been recorded"):
        journal.record_actual("another action", "another reason")


def test_tampering_and_backdated_actual_are_rejected(tmp_path):
    fixed = datetime(2026, 9, 24, 1, 0, tzinfo=timezone.utc)
    journal = ProspectiveJournal(tmp_path / "journal", now=lambda: fixed)
    journal.issue(*inputs())
    with pytest.raises(ValueError, match="after prediction"):
        journal.record_actual("A", "B")
    prediction = journal.directory / "prediction.json"
    prediction.write_text(prediction.read_text().replace("moderate", "high"))
    with pytest.raises(ValueError, match="evidence file changed"):
        journal.verify()


def test_cli_action_is_not_confused_with_subcommand(tmp_path, capsys):
    directory = tmp_path / "journal"
    assert main(["issue", str(CASE / "decisions.json"), str(CASE / "scenario.json"), str(directory)]) == 0
    capsys.readouterr()
    assert main(["record-actual", str(directory), "--action", "Take a short trial", "--reason", "Time is limited"]) == 0
    assert json.loads(capsys.readouterr().out)["actual_action"] == "Take a short trial"
    assert main(["verify", str(directory)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "compared"


def test_invalid_issue_does_not_create_journal(tmp_path):
    directory = tmp_path / "journal"
    with pytest.raises(ValueError, match="records"):
        ProspectiveJournal(directory).issue([], inputs()[1])
    assert not directory.exists()
