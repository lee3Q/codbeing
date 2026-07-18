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


def validate_decision_trace(trace: Any) -> None:
    """Raise a clear error unless *trace* contains every required field."""
    if not isinstance(trace, Mapping):
        raise DecisionTraceValidationError(
            "DecisionTrace must be a JSON object containing required fields."
        )

    missing_fields = [field for field in REQUIRED_FIELDS if field not in trace]
    if missing_fields:
        missing_list = ", ".join(missing_fields)
        raise DecisionTraceValidationError(f"missing required fields: {missing_list}")
