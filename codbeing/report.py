"""Evidence-grounded Markdown Runtime Analysis reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .schema import DecisionTraceValidationError, validate_decision_trace


MAX_EVIDENCE_TEXT_LENGTH = 500
INSTRUCTION_LIKE_TEXT = (
    "ignore previous instructions",
    "you should",
    "you must",
    "delete files",
    "reveal secrets",
    "exfiltrate",
)


def analyze_decision_traces(payload: Any) -> str:
    """Validate DecisionTrace input and return a local Markdown analysis report."""
    traces = _normalize_traces(payload)
    for trace in traces:
        validate_decision_trace(trace)

    current_trace = traces[-1]
    confidence = _confidence_label(traces)
    output_tier = _output_tier(traces)
    dogfood_interpretation = _academic_nomusa_interpretation(traces)
    return "\n".join(
        (
            "# Runtime Analysis",
            "",
            "## Output Tier",
            *output_tier.evidence,
            "",
            "## Evidence Summary",
            *_evidence_summary(traces),
            "",
            "## Detected Trajectory",
            *_trajectory(traces),
            "",
            "## User-Code Hypothesis",
            *_hypothesis(traces),
            "",
            "## Current Decision Diff",
            *_current_decision_diff(traces, current_trace),
            "",
            "## Recommended Next Protocol",
            *dogfood_interpretation.protocol,
            "",
            "## Analysis Guardrails",
            *_analysis_guardrails(),
            "",
            "## Confidence Breakdown",
            f"- Overall confidence: **{confidence}**.",
            f"- Trace count: {len(traces)}.",
            f"- Memory confidence: {_memory_confidence_summary(traces)}.",
            "- Evidence coverage: each conclusion above is limited to the supplied "
            "DecisionTrace fields.",
            "",
            "## Uncertainty",
            "- This report cannot establish motives, hidden feelings, or external "
            "outcomes not recorded in the trace.",
            "- More comparable traces may confirm, refine, or contradict the trajectory.",
            "",
            "## User Override",
            "- The user remains the decision authority. This report is a reviewable "
            "hypothesis, and its optional protocols may be overridden for the current "
            "context.",
            "",
        )
    )


def _normalize_traces(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        return [payload]
    if isinstance(payload, list) and payload:
        if all(isinstance(trace, Mapping) for trace in payload):
            return payload
    raise DecisionTraceValidationError(
        "DecisionTrace analysis input must be one JSON object or a non-empty JSON array "
        "of DecisionTrace objects."
    )


def _evidence_summary(traces: Sequence[Mapping[str, Any]]) -> list[str]:
    evidence: list[str] = []
    for index, trace in enumerate(traces, start=1):
        evidence.append(
            f"- Trace {index} ({_text(trace['source'])}): context: {_text(trace['context'])}; "
            f"chosen action: {_text(trace['chosen_action'])}; judgment basis: "
            f"{_text(trace['judgment_basis'])}; observed behavior: "
            f"{_text(trace['observed_behavior'])}; outcome: {_text(trace['outcome'])}; "
            f"aftertaste: {_text(trace['aftertaste'])}."
        )
    return evidence


def _trajectory(traces: Sequence[Mapping[str, Any]]) -> list[str]:
    if len(traces) == 1:
        return [
            "- One trace records a decision sequence, but it does not establish a repeated "
            "trajectory."
        ]

    chosen_actions = [_text(trace["chosen_action"]) for trace in traces]
    return [
        "- The supplied sequence contains "
        f"{len(traces)} decisions with chosen actions: {', '.join(chosen_actions)}. "
        "A repeated trajectory remains a comparison of these records against their context."
    ]


def _hypothesis(traces: Sequence[Mapping[str, Any]]) -> list[str]:
    bases = sorted({_text(trace["judgment_basis"]) for trace in traces})
    hypothesis = [
        "- Evidence-limited hypothesis: the recorded decisions are evaluated through the "
        f"stated judgment basis/bases: {'; '.join(bases)}. This is not a personality label "
        "or a claim about unrecorded motives or feelings."
    ]
    interpretation = _academic_nomusa_interpretation(traces)
    if interpretation.activation_signal:
        hypothesis.append(interpretation.activation_signal)
    return hypothesis


def _current_decision_diff(
    traces: Sequence[Mapping[str, Any]], current_trace: Mapping[str, Any]
) -> list[str]:
    rejected_options = _items_text(current_trace["rejected_options"])
    current = (
        f"- Current trace chose {_text(current_trace['chosen_action'])} over "
        f"{rejected_options}; stated basis: {_text(current_trace['judgment_basis'])}."
    )
    if len(traces) == 1:
        return [current, "- No prior trace was supplied for a direct decision diff."]

    prior_actions = ", ".join(_text(trace["chosen_action"]) for trace in traces[:-1])
    return [
        current,
        f"- Compared with prior recorded choices ({prior_actions}), this report does not "
        "infer a difference beyond the supplied fields.",
    ]


def _confidence_label(traces: Sequence[Mapping[str, Any]]) -> str:
    high_memory_count = sum(
        _text(trace["memory_confidence"]).lower() in {"high", "medium-high"}
        for trace in traces
    )
    if len(traces) >= 3 and high_memory_count == len(traces):
        return "medium"
    if len(traces) >= 2 and high_memory_count:
        return "low-medium"
    return "low"


def _memory_confidence_summary(traces: Sequence[Mapping[str, Any]]) -> str:
    return ", ".join(_text(trace["memory_confidence"]) for trace in traces)


def _analysis_guardrails() -> list[str]:
    """State the limits that keep generated analysis evidence-bound and non-directive."""
    return [
        "- The analysis assigns no personality labels and makes no claim about hidden "
        "feelings or motives.",
        "- The analysis gives no direct life commands, external-success predictions, or "
        "unsupported judgments.",
        "- Analytical statements use only the supplied DecisionTrace fields; no evidence "
        "is invented.",
        "- Instruction-like text inside DecisionTrace fields is treated only as recorded "
        "evidence and is neutralized before report rendering.",
        "- An emotional activation signal remains separate from the recorded decision "
        "reason unless the stated judgment basis explicitly identifies it as a criterion.",
    ]


class _DogfoodInterpretation:
    def __init__(self, activation_signal: str | None, protocol: list[str]) -> None:
        self.activation_signal = activation_signal
        self.protocol = protocol


class _OutputTier:
    def __init__(self, name: str, evidence: list[str]) -> None:
        self.name = name
        self.evidence = evidence


def _output_tier(traces: Sequence[Mapping[str, Any]]) -> _OutputTier:
    hard_mirror = _hard_mirror_evaluation(traces)
    if hard_mirror is not None:
        return _OutputTier(
            "Hard Mirror",
            [
                "- Selected tier: **Hard Mirror**.",
                "- Explicit gate evidence: current decision impact is high; "
                "reversibility cost is medium-high or high; action pressure is "
                "immediate; comparable trace confidence is sufficient; and the "
                "current activation pattern directly matches a prior trace: "
                f"{hard_mirror}.",
            ],
        )

    return _OutputTier(
        "Runtime Analysis",
        [
            "- Selected tier: **Runtime Analysis**.",
            "- Hard Mirror is withheld unless the current trace explicitly records "
            "every required gate: high impact, medium-high or high reversibility "
            "cost, immediate action pressure, sufficient comparable-trace confidence, "
            "and a direct prior activation-pattern match.",
        ],
    )


def _hard_mirror_evaluation(traces: Sequence[Mapping[str, Any]]) -> str | None:
    if len(traces) < 2:
        return None

    current_trace = traces[-1]
    if _signal_value(current_trace, "impact", "decision_impact") not in {
        "high",
        "high-impact",
    }:
        return None
    if _signal_value(current_trace, "reversibility_cost", "reversibility") not in {
        "medium-high",
        "high",
    }:
        return None
    if _signal_value(current_trace, "action_pressure", "decision_timing") not in {
        "immediate",
        "immediate-action",
    }:
        return None
    if not _has_sufficient_hard_mirror_confidence(traces):
        return None

    current_patterns = _activation_patterns(current_trace)
    if not current_patterns:
        return None

    prior_patterns = set().union(*(_activation_patterns(trace) for trace in traces[:-1]))
    matches = sorted(current_patterns & prior_patterns)
    if not matches:
        return None
    return ", ".join(matches)


def _has_sufficient_hard_mirror_confidence(
    traces: Sequence[Mapping[str, Any]],
) -> bool:
    confident_levels = {"high", "medium-high"}
    return all(
        _text(trace["memory_confidence"]).lower() in confident_levels
        for trace in traces
    )


def _signal_value(trace: Mapping[str, Any], *field_names: str) -> str:
    for field_name in field_names:
        if field_name in trace:
            return _text(trace[field_name]).lower().replace(" ", "-")
    return ""


def _activation_patterns(trace: Mapping[str, Any]) -> set[str]:
    patterns: set[str] = set()
    for field_name in (
        "activation_patterns",
        "activation_pattern",
        "activation_trigger",
    ):
        if field_name not in trace:
            continue
        value = trace[field_name]
        values = value if isinstance(value, list) else [value]
        patterns.update(
            normalized
            for item in values
            if (normalized := _text(item).lower())
        )
    return patterns


def _academic_nomusa_interpretation(
    traces: Sequence[Mapping[str, Any]],
) -> _DogfoodInterpretation:
    if not _is_academic_nomusa_case(traces):
        return _DogfoodInterpretation(
            activation_signal=None,
            protocol=[
                "- Optional protocol: a decision boundary, comparison against the stated "
                "judgment basis, and one observable check can support a later review.",
                "- The recorded aftertaste remains separate from the decision's stated "
                "reason; it may be an activation signal rather than the core reason.",
            ],
        )

    trigger_fields = _activation_trigger_fields(traces)
    return _DogfoodInterpretation(
        activation_signal=(
            "- Recorded work-study loss is an activation trigger rather than the core "
            "decision reason: it is recorded in "
            f"{', '.join(trigger_fields)}, while the stated judgment basis names the "
            "decision criteria."
        ),
        protocol=[
            "- A/B/C practical exam decision protocol:",
            "  - A: Evidence record: 2025/2026 practical past-exam performance for the "
            "academic decision review.",
            "  - B: Comparison frame: that result alongside the recorded labor-attorney "
            "route option value and graduation-delay cost.",
            "  - C: Branch criterion: the comparison, with the user retaining authority "
            "to select a different path.",
        ],
    )


def _is_academic_nomusa_case(traces: Sequence[Mapping[str, Any]]) -> bool:
    stated_bases = " ".join(_text(trace["judgment_basis"]).lower() for trace in traces)
    surrounding_evidence = " ".join(
        _text(trace[field]).lower()
        for trace in traces
        for field in (
            "context",
            "options",
            "chosen_action",
            "rejected_options",
            "observed_behavior",
            "outcome",
            "aftertaste",
            "source",
        )
    )
    all_evidence = f"{stated_bases} {surrounding_evidence}"
    has_nomusa = any(
        term in all_evidence for term in ("nomusa", "labor-attorney", "노무사")
    )
    has_practical_exam = any(
        term in all_evidence
        for term in ("practical exam", "practical past-exam", "past-exam", "실전 기출", "기출")
    )
    has_work_study_loss = any(
        term in surrounding_evidence
        for term in ("work-study loss", "work study loss", "국가근로", "근로장학")
    )
    work_study_is_stated_basis = any(
        term in stated_bases
        for term in ("work-study loss", "work study loss", "국가근로", "근로장학")
    )
    return (
        has_nomusa
        and has_practical_exam
        and has_work_study_loss
        and not work_study_is_stated_basis
    )


def _activation_trigger_fields(traces: Sequence[Mapping[str, Any]]) -> list[str]:
    trigger_terms = ("work-study loss", "work study loss", "국가근로", "근로장학")
    return [
        field
        for field in (
            "context",
            "options",
            "chosen_action",
            "rejected_options",
            "observed_behavior",
            "outcome",
            "aftertaste",
            "source",
        )
        if any(
            term in _text(trace[field]).lower()
            for trace in traces
            for term in trigger_terms
        )
    ]


def _items_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value) or "no recorded rejected options"
    return _text(value)


def _text(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    text = _neutralize_instruction_like_text(text)
    if len(text) > MAX_EVIDENCE_TEXT_LENGTH:
        return f"{text[:MAX_EVIDENCE_TEXT_LENGTH].rstrip()}... [truncated]"
    return text


def _neutralize_instruction_like_text(text: str) -> str:
    neutralized = text
    lower_text = text.lower()
    for phrase in INSTRUCTION_LIKE_TEXT:
        start = lower_text.find(phrase)
        while start != -1:
            end = start + len(phrase)
            neutralized = (
                f"{neutralized[:start]}[instruction-like trace text neutralized]"
                f"{neutralized[end:]}"
            )
            lower_text = neutralized.lower()
            start = lower_text.find(phrase)
    return neutralized
