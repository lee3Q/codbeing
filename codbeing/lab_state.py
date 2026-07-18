"""Local research-state loading for the codbeing lab."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import DecisionTraceValidationError, validate_decision_trace


@dataclass(frozen=True)
class ResearchState:
    """A safe snapshot of the single ongoing local research study."""

    traces: tuple[dict[str, Any], ...]
    trace_store_has_issue: bool
    reports: tuple[Path, ...]
    latest_report: Path | None
    reports_directory_has_issue: bool
    submitted_material: tuple[str, ...]
    submitted_material_store_has_issue: bool

    @property
    def trace_count(self) -> int:
        return len(self.traces)

    @property
    def submitted_material_count(self) -> int:
        return len(self.submitted_material)


@dataclass(frozen=True)
class ResearchStateSummary:
    """Short, display-ready local research-state summary."""

    evidence: str
    analysis: str
    apparatus: tuple[str, ...]
    warnings: tuple[str, ...]


def load_research_state(
    trace_store: Path,
    reports_dir: Path,
    submitted_material_store: Path | None = None,
) -> ResearchState:
    """Load readable local evidence and reports without failing on partial state."""
    traces, trace_store_has_issue = _load_readable_traces(trace_store)
    reports, reports_directory_has_issue = _load_reports(reports_dir)
    submitted_material, submitted_material_store_has_issue = _load_submitted_material(
        submitted_material_store
    )
    latest_report = reports[0] if reports else None
    return ResearchState(
        traces=tuple(traces),
        trace_store_has_issue=trace_store_has_issue,
        reports=tuple(reports),
        latest_report=latest_report,
        reports_directory_has_issue=reports_directory_has_issue,
        submitted_material=tuple(submitted_material),
        submitted_material_store_has_issue=submitted_material_store_has_issue,
    )


def append_submitted_material(path: Path, material: str) -> int:
    """Append one non-empty private lab note to a local JSON store."""
    normalized_material = material.strip()
    if not normalized_material:
        raise ValueError("submitted material cannot be empty")

    submitted_material, has_issue = _load_submitted_material(path)
    if has_issue:
        raise ValueError("submitted material store needs repair before new material can be saved")

    submitted_material.append(normalized_material)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(submitted_material, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(submitted_material)


def summarize_research_state(state: ResearchState) -> ResearchStateSummary:
    """Describe the available local research apparatus without requiring an LLM."""
    if state.trace_store_has_issue:
        evidence = "local DecisionTrace store needs repair before it can be fully read."
    elif state.trace_count:
        noun = "DecisionTrace" if state.trace_count == 1 else "DecisionTraces"
        evidence = f"{state.trace_count} stored {noun}"
    else:
        evidence = "no submitted DecisionTraces yet"

    if state.latest_report is None:
        analysis = "no local reports yet"
    else:
        analysis = f"latest local report is {state.latest_report.name}"

    apparatus = ["Evidence"]
    if state.trace_count:
        apparatus.append("Self Code")
        apparatus.append("Simulation")
    if state.latest_report is not None:
        apparatus.append("Analysis")

    warnings: list[str] = []
    if state.trace_store_has_issue:
        warnings.append("Some saved DecisionTrace evidence could not be read.")
    if state.reports_directory_has_issue:
        warnings.append("Some local report metadata could not be read.")
    if state.submitted_material_store_has_issue:
        warnings.append("Some submitted local material could not be read.")

    return ResearchStateSummary(
        evidence=evidence,
        analysis=analysis,
        apparatus=tuple(apparatus),
        warnings=tuple(warnings),
    )


def _load_readable_traces(path: Path) -> tuple[list[dict[str, Any]], bool]:
    if not path.exists():
        return [], False

    try:
        with path.open(encoding="utf-8") as trace_handle:
            payload = json.load(trace_handle)
    except (OSError, json.JSONDecodeError):
        return [], True

    candidates = [payload] if isinstance(payload, Mapping) else payload
    if not isinstance(candidates, list):
        return [], True

    traces: list[dict[str, Any]] = []
    has_issue = False
    for candidate in candidates:
        try:
            validate_decision_trace(candidate)
        except DecisionTraceValidationError:
            has_issue = True
            continue
        traces.append(dict(candidate))
    return traces, has_issue


def _load_reports(reports_dir: Path) -> tuple[list[Path], bool]:
    if not reports_dir.exists():
        return [], False
    if not reports_dir.is_dir():
        return [], True

    reports: list[tuple[float, Path]] = []
    has_issue = False
    try:
        report_paths = reports_dir.glob("*.md")
        for report_path in report_paths:
            if not report_path.is_file():
                continue
            try:
                reports.append((report_path.stat().st_mtime, report_path))
            except OSError:
                has_issue = True
    except OSError:
        return [], True

    reports.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    return [path for _, path in reports], has_issue


def _load_submitted_material(path: Path | None) -> tuple[list[str], bool]:
    if path is None or not path.exists():
        return [], False

    try:
        with path.open(encoding="utf-8") as material_handle:
            payload = json.load(material_handle)
    except (OSError, json.JSONDecodeError):
        return [], True

    if not isinstance(payload, list) or not all(isinstance(item, str) and item.strip() for item in payload):
        return [], True

    return [item.strip() for item in payload], False
