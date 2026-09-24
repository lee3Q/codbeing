"""Issue a frozen prediction before accepting a later actual choice."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from codbeing.research_cycle import _read, _text, _timestamp, build_model, compare, predict


GENESIS = "0" * 64


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(_bytes(value))


class ProspectiveJournal:
    """Local two-event journal; file creation and timestamps are controlled here."""

    def __init__(self, directory: Path, *, now: Callable[[], datetime] | None = None):
        self.directory = directory.resolve()
        self.now = now or (lambda: datetime.now(timezone.utc))

    def _event(self, sequence: int, previous: str, kind: str, files: list[str], recorded_at: str) -> dict[str, Any]:
        event = {"sequence": sequence, "previous_hash": previous, "kind": kind,
                 "recorded_at": recorded_at,
                 "files": {name: hashlib.sha256((self.directory / name).read_bytes()).hexdigest() for name in files}}
        event["event_hash"] = _hash(event)
        return event

    def _events(self) -> list[dict[str, Any]]:
        path = self.directory / "events.jsonl"
        if not path.is_file():
            raise ValueError("prediction has not been issued")
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or len(lines) > 2:
            raise ValueError("invalid event count")
        events, previous = [], GENESIS
        for index, line in enumerate(lines, 1):
            event = json.loads(line)
            if (event.get("sequence") != index or event.get("previous_hash") != previous
                or event.get("event_hash") != _hash({key: value for key, value in event.items() if key != "event_hash"})
                or event.get("kind") != ("prediction_issued" if index == 1 else "actual_recorded")):
                raise ValueError("broken prospective event chain")
            for name, digest in event.get("files", {}).items():
                if name not in ("records.json", "scenario.json", "model.json", "prediction.json", "actual.json", "comparison.json"):
                    raise ValueError("unexpected evidence file")
                if hashlib.sha256((self.directory / name).read_bytes()).hexdigest() != digest:
                    raise ValueError(f"evidence file changed: {name}")
            previous = event["event_hash"]
            events.append(event)
        if set(events[0]["files"]) != {"records.json", "scenario.json", "model.json", "prediction.json"}:
            raise ValueError("incomplete prediction evidence")
        if len(events) == 2 and set(events[1]["files"]) != {"actual.json", "comparison.json"}:
            raise ValueError("incomplete actual evidence")
        return events

    def issue(self, records: Any, scenario: Any) -> dict[str, Any]:
        timestamp = self.now().astimezone(timezone.utc).isoformat()
        model = build_model(records)
        card = predict(model, scenario, predicted_at=timestamp)
        self.directory.mkdir(parents=True, exist_ok=False)
        for name, value in (("records.json", records), ("scenario.json", scenario),
                            ("model.json", model), ("prediction.json", card)):
            _write_new(self.directory / name, value)
        event = self._event(1, GENESIS, "prediction_issued",
                            ["records.json", "scenario.json", "model.json", "prediction.json"], timestamp)
        with (self.directory / "events.jsonl").open("x", encoding="utf-8") as stream:
            stream.write(_bytes(event).decode("utf-8"))
        return card

    def record_actual(self, action: str, reason: str) -> dict[str, Any]:
        action = _text(action, "actual.action")
        reason = _text(reason, "actual.reason")
        events = self._events()
        if len(events) != 1:
            raise ValueError("actual choice has already been recorded")
        timestamp = self.now().astimezone(timezone.utc).isoformat()
        if _timestamp(timestamp, "recorded_at") <= _timestamp(events[0]["recorded_at"], "issued_at"):
            raise ValueError("actual choice must be entered after prediction issuance")
        card = _read(self.directory / "prediction.json")
        actual = {"scenario_id": card["scenario_id"], "recorded_at": timestamp,
                  "action": action, "reason": reason}
        comparison = compare(card, actual)
        _write_new(self.directory / "actual.json", actual)
        _write_new(self.directory / "comparison.json", comparison)
        event = self._event(2, events[0]["event_hash"], "actual_recorded",
                            ["actual.json", "comparison.json"], timestamp)
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(_bytes(event).decode("utf-8"))
        return comparison

    def verify(self, *, expected_head: str | None = None) -> dict[str, Any]:
        events = self._events()
        model = build_model(_read(self.directory / "records.json"))
        if model != _read(self.directory / "model.json"):
            raise ValueError("model does not reproduce")
        card = predict(model, _read(self.directory / "scenario.json"),
                       predicted_at=events[0]["recorded_at"])
        if card != _read(self.directory / "prediction.json"):
            raise ValueError("prediction does not reproduce")
        if len(events) == 2:
            if _timestamp(events[1]["recorded_at"], "actual_recorded_at") <= _timestamp(events[0]["recorded_at"], "issued_at"):
                raise ValueError("event order and timestamps disagree")
            if compare(card, _read(self.directory / "actual.json")) != _read(self.directory / "comparison.json"):
                raise ValueError("comparison does not reproduce")
        head = events[-1]["event_hash"]
        if expected_head is not None and head != expected_head:
            raise ValueError("journal head differs from external anchor")
        return {"status": "compared" if len(events) == 2 else "awaiting_actual",
                "model_id": model["model_id"], "prediction_id": card["prediction_id"], "head": head}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("issue")
    issue.add_argument("records", type=Path)
    issue.add_argument("scenario", type=Path)
    issue.add_argument("directory", type=Path)
    actual = sub.add_parser("record-actual")
    actual.add_argument("directory", type=Path)
    actual.add_argument("--action", dest="decision_action", required=True)
    actual.add_argument("--reason", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--expected-head")
    args = parser.parse_args(argv)
    try:
        journal = ProspectiveJournal(args.directory)
        if args.command == "issue":
            result = journal.issue(_read(args.records), _read(args.scenario))
        elif args.command == "record-actual":
            result = journal.record_actual(args.decision_action, args.reason)
        else:
            result = journal.verify(expected_head=args.expected_head)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"prospective journal error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
