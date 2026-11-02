"""DecisionTrace schema validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


REQUIRED_FIELDS = (
    "context",
    "options",
    "chosen_action",
    "rejected_options",
    "judgment_basis",
    "observed_behavior",
    "outcome",
    "aftertaste",
    "memory_confidence",
    "source",
)


class DecisionTraceValidationError(ValueError):
    """Raised when a DecisionTrace does not meet the minimum schema."""


def validate_decision_trace(trace: Any, *, require_core: bool = False) -> None:
    """Validate structure without inventing missing decision evidence.

    Core evidence must contain text. Supporting observations may be empty when
    unknown or withheld. Extra fields remain allowed for existing extensions.
    """
    if not isinstance(trace, Mapping):
        raise DecisionTraceValidationError(
            "DecisionTrace must be a JSON object containing required fields."
        )

    missing_fields = [field for field in REQUIRED_FIELDS if field not in trace]
    if missing_fields:
        missing_list = ", ".join(missing_fields)
        raise DecisionTraceValidationError(f"missing required fields: {missing_list}")

    if not require_core:
        return

    list_fields = ("options", "rejected_options")
    for field in REQUIRED_FIELDS:
        value = trace[field]
        if field in list_fields:
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise DecisionTraceValidationError(
                    f"{field} must be an array of non-blank strings."
                )
        elif not isinstance(value, str):
            raise DecisionTraceValidationError(f"{field} must be a string.")

    for field in ("context", "chosen_action", "judgment_basis"):
        if not trace[field].strip():
            raise DecisionTraceValidationError(f"{field} must not be blank.")
    if not trace["options"]:
        raise DecisionTraceValidationError("options must contain at least one option.")
