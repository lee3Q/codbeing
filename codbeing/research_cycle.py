"""Reproducible, local decision-model prediction and prospective comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_VERSION = "direct-decision-v1"
REVIEWED_VERSION = "reviewed-evidence-v2"
SUPPLEMENTAL_SOURCES = {"conversation", "memo", "behavior"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_immutable(path: Path, value: Any) -> None:
    """Do not replace a previously issued model or prediction card."""
    if path.exists():
        if _read(path) != value:
            raise ValueError(f"existing artifact cannot be replaced: {path}")
        return
    _write(path, value)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _tags(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a non-empty string list")
    return sorted(set(item.strip() for item in value))


def _timestamp(value: Any, field: str) -> datetime:
    raw = _text(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _reviewed(record: dict[str, Any]) -> dict[str, str | bool]:
    review = record.get("review")
    if not isinstance(review, dict) or review.get("approved_by_user") is not True:
        raise ValueError("additional evidence requires explicit user approval")
    reviewed_at = _text(review.get("reviewed_at"), "review.reviewed_at")
    _timestamp(reviewed_at, "review.reviewed_at")
    return {"approved_by_user": True, "reviewed_at": reviewed_at}


def _detailed(value: Any, field: str) -> str:
    detail = _text(value, field)
    if len(detail) < 30:
        raise ValueError(f"{field} needs at least 30 characters of explanation")
    return detail


def build_model(records: Any) -> dict[str, Any]:
    """Build a new snapshot from direct decisions and explicitly reviewed evidence."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    decisions = []
    ids = set()
    has_additional_evidence = False
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be an object")
        source = record.get("source_type")
        if source != "direct_decision" and source not in SUPPLEMENTAL_SOURCES and source != "actual_choice":
            raise ValueError("unsupported evidence source_type")
        decision = {key: _text(record.get(key), key) for key in ("id", "situation", "action", "reason", "pressure")}
        decision["conditions"] = _tags(record.get("conditions"), "conditions")
        decision["alternatives"] = _tags(record.get("alternatives"), "alternatives")
        if source != "direct_decision":
            has_additional_evidence = True
            decision["source_type"] = source
            decision["review"] = _reviewed(record)
            if source in SUPPLEMENTAL_SOURCES:
                decision["context"] = _detailed(record.get("context"), "context")
                decision["meaning"] = _detailed(record.get("meaning"), "meaning")
            else:
                decision["prediction_id"] = _text(record.get("prediction_id"), "prediction_id")
                decision["recorded_at"] = _text(record.get("recorded_at"), "recorded_at")
                if _timestamp(decision["recorded_at"], "recorded_at") > _timestamp(decision["review"]["reviewed_at"], "review.reviewed_at"):
                    raise ValueError("actual choice must be reviewed after it is recorded")
        if decision["id"] in ids:
            raise ValueError("decision ids must be unique")
        ids.add(decision["id"])
        decisions.append(decision)
    model = {"version": REVIEWED_VERSION if has_additional_evidence else MODEL_VERSION, "evidence": decisions}
    model["model_id"] = _digest(model)
    return model


def predict(model: Any, scenario: Any, *, predicted_at: str | None = None) -> dict[str, Any]:
    """Make an auditable hypothesis from the closest evidence in this snapshot."""
    if not isinstance(model, dict) or model.get("version") not in (MODEL_VERSION, REVIEWED_VERSION) or not model.get("evidence"):
        raise ValueError("unsupported or empty model")
    expected = _digest({"version": model["version"], "evidence": model["evidence"]})
    if model.get("model_id") != expected:
        raise ValueError("model integrity check failed")
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be an object")
    scenario_id = _text(scenario.get("id"), "scenario.id")
    _text(scenario.get("situation"), "scenario.situation")
    conditions = set(_tags(scenario.get("conditions"), "scenario.conditions"))
    ranked = sorted(
        model["evidence"],
        key=lambda item: (-len(conditions & set(item["conditions"])), item["id"]),
    )
    best = ranked[0]
    overlap = len(conditions & set(best["conditions"]))
    if overlap == 0:
        raise ValueError("no comparable direct decision; prediction withheld")
    confidence = "moderate" if overlap >= 2 and len(ranked) >= 2 else "low"
    timestamp = predicted_at or datetime.now(timezone.utc).isoformat()
    _timestamp(timestamp, "predicted_at")
    card = {
        "scenario_id": scenario_id,
        "predicted_at": timestamp,
        "model_version": model["version"],
        "model_id": model["model_id"],
        "evidence_ids": [best["id"]],
        "action": best["action"],
        "reason": best["reason"],
        "pressure_emotion": best["pressure"],
        "alternatives": best["alternatives"],
        "confidence": confidence,
        "matched_conditions": sorted(conditions & set(best["conditions"])),
        "status": "hypothesis; user retains decision authority",
    }
    card["prediction_id"] = _digest(card)
    return card


def compare(card: Any, actual: Any) -> dict[str, Any]:
    """Keep the later choice separate from the frozen prediction."""
    if not isinstance(card, dict) or card.get("prediction_id") != _digest({k: v for k, v in card.items() if k != "prediction_id"}):
        raise ValueError("prediction integrity check failed")
    if not isinstance(actual, dict) or actual.get("scenario_id") != card["scenario_id"]:
        raise ValueError("actual choice must match the predicted scenario")
    action = _text(actual.get("action"), "actual.action")
    recorded_at = _text(actual.get("recorded_at"), "actual.recorded_at")
    if _timestamp(recorded_at, "actual.recorded_at") <= _timestamp(card["predicted_at"], "predicted_at"):
        raise ValueError("actual choice must be recorded after prediction")
    return {
        "prediction_id": card["prediction_id"],
        "scenario_id": card["scenario_id"],
        "predicted_action": card["action"],
        "actual_action": action,
        "actual_recorded_at": recorded_at,
        "actual_reason": _text(actual.get("reason"), "actual.reason"),
        "action_match": action == card["action"],
        "note": "One prospective comparison; it does not validate general predictive accuracy.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    model_cmd = sub.add_parser("model")
    model_cmd.add_argument("records", type=Path)
    model_cmd.add_argument("output", type=Path)
    predict_cmd = sub.add_parser("predict")
    predict_cmd.add_argument("model", type=Path)
    predict_cmd.add_argument("scenario", type=Path)
    predict_cmd.add_argument("output", type=Path)
    predict_cmd.add_argument("--at", help="Fixed timestamp for reproducible synthetic examples")
    compare_cmd = sub.add_parser("compare")
    compare_cmd.add_argument("prediction", type=Path)
    compare_cmd.add_argument("actual", type=Path)
    compare_cmd.add_argument("output", type=Path)
    verify_cmd = sub.add_parser("verify")
    for name in ("records", "scenario", "actual", "model", "prediction", "comparison", "receipt"):
        verify_cmd.add_argument(name, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "model":
            _write_immutable(args.output, build_model(_read(args.records)))
        elif args.command == "predict":
            _write_immutable(args.output, predict(_read(args.model), _read(args.scenario), predicted_at=args.at))
        elif args.command == "compare":
            _write(args.output, compare(_read(args.prediction), _read(args.actual)))
        else:
            records = _read(args.records)
            stored_card = _read(args.prediction)
            actual = _read(args.actual)
            model = build_model(records)
            card = predict(model, _read(args.scenario), predicted_at=stored_card["predicted_at"])
            comparison = compare(card, actual)
            checks = {
                "model_matches": model == _read(args.model),
                "prediction_matches": card == stored_card,
                "comparison_matches": comparison == _read(args.comparison),
                "prediction_precedes_actual": _timestamp(stored_card["predicted_at"], "predicted_at") < _timestamp(actual["recorded_at"], "recorded_at"),
                "direct_decision_evidence_only": all(isinstance(item, dict) and item.get("source_type") == "direct_decision" for item in records),
            }
            receipt = {"stage": "stage_1_public_reproduction", "checks": checks, "passed": all(checks.values()), "stage_2_future_choice_study": "pending"}
            _write(args.receipt, receipt)
            if not receipt["passed"]:
                raise ValueError("reproduction checks failed")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"research cycle error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
