"""Command-line entry point for codbeing."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from .config import (
    CodbeingConfig,
    DEFAULT_CONFIG_PATH,
    PROVIDERS,
    config_summary,
    load_config,
    resolve_provider,
    save_config,
)
from .lab_state import (
    ResearchState,
    ResearchStateSummary,
    append_submitted_material,
    load_research_state,
    summarize_research_state,
)
from .models import external_assist_ready, model_assist_section
from .report import analyze_decision_traces
from .schema import DecisionTraceValidationError, validate_decision_trace


DEFAULT_TRACE_STORE = Path("private-traces/decision-traces.json")
DEFAULT_REPORTS_DIR = Path("private-reports")
DEFAULT_SUBMITTED_MATERIAL_STORE = Path("private-traces/submitted-material.json")
LAB_STATE_FIXTURE_ENV = "CODBEING_LAB_STATE_FIXTURE"


ACADEMIC_NOMUSA_TRACES: list[dict[str, Any]] = [
    {
        "context": "Compare the academic leave decision with the Nomusa route.",
        "options": ["Stay enrolled", "Take academic leave"],
        "chosen_action": "Defer the leave decision until practical past-exam evidence exists.",
        "rejected_options": ["Decide from work-study loss alone"],
        "judgment_basis": (
            "Compare the labor-attorney route's option value and graduation-delay cost "
            "using 2025 practical past-exam performance."
        ),
        "observed_behavior": "Outlined a 2025/2026 practical exam branch criterion.",
        "outcome": "Academic leave remains undecided pending the criterion.",
        "aftertaste": "The work-study loss created urgency.",
        "memory_confidence": "high",
        "source": "sanitized academic dogfood fixture",
    },
    {
        "context": "Review the Nomusa route after a second practical past-exam attempt.",
        "options": ["Continue the route", "Revisit academic leave"],
        "chosen_action": "Use the recorded branch criterion.",
        "rejected_options": ["Treat urgency as the reason"],
        "judgment_basis": (
            "Use 2026 practical past-exam performance to compare option value with "
            "graduation-delay cost."
        ),
        "observed_behavior": "Kept the work-study loss separate from the evaluation criteria.",
        "outcome": "The practical exam result will determine the next review.",
        "aftertaste": "Work-study loss remains an activation signal.",
        "memory_confidence": "high",
        "source": "sanitized Nomusa dogfood fixture",
    },
]


class KoreanArgumentParser(argparse.ArgumentParser):
    """Show Korean-first guidance while retaining argparse's specific reason."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 입력 오류입니다. 명령과 옵션을 확인해 주세요. {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = KoreanArgumentParser(
        prog="cb",
        description="Capture, validate, and analyze local DecisionTrace JSON files.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Local codbeing config path.",
    )
    parser.add_argument(
        "--lab-state",
        action="store_true",
        help="Print the isolated machine-readable lab state when used with --json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print supported machine-readable output as compact JSON.",
    )
    subparsers = parser.add_subparsers(dest="command")

    validate_parser = subparsers.add_parser(
        "validate", help="Validate one DecisionTrace JSON object."
    )
    validate_parser.add_argument("trace_file", type=Path)

    analyze_parser = subparsers.add_parser(
        "analyze", help="Create a Markdown Runtime Analysis report."
    )
    analyze_parser.add_argument("trace_file", type=Path)
    analyze_parser.add_argument("report_file", type=Path)
    _add_model_argument(analyze_parser)

    for name in ("quick", "run"):
        quick_parser = subparsers.add_parser(
            name,
            help="Validate and analyze a trace file in one command with an automatic report path.",
        )
        quick_parser.add_argument("trace_file", type=Path, nargs="?")
        quick_parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
        quick_parser.add_argument("--name", help="Report filename stem.")
        _add_model_argument(quick_parser)

    capture_parser = subparsers.add_parser(
        "capture", help="Interactively append one DecisionTrace and analyze the accumulated store."
    )
    capture_parser.add_argument("--store", type=Path, default=DEFAULT_TRACE_STORE)
    capture_parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    capture_parser.add_argument("--name", help="Report filename stem.")
    capture_parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Only append the trace; do not write a report.",
    )
    _add_model_argument(capture_parser)

    example_parser = subparsers.add_parser(
        "example", help="Create a private fixture from a known dogfooding example."
    )
    example_subparsers = example_parser.add_subparsers(
        dest="example_name", required=True
    )
    nomusa_parser = example_subparsers.add_parser(
        "nomusa", help="Write the academic/Nomusa dogfooding fixture and report."
    )
    nomusa_parser.add_argument(
        "--trace-file",
        type=Path,
        default=Path("private-traces/academic-nomusa.json"),
    )
    nomusa_parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    nomusa_parser.add_argument("--name", default="academic-nomusa")
    _add_model_argument(nomusa_parser)

    model_parser = subparsers.add_parser(
        "model", help="Show or change the selected report execution model."
    )
    model_subparsers = model_parser.add_subparsers(dest="model_command")
    model_subparsers.add_parser("status", help="Show current model configuration.")
    use_parser = model_subparsers.add_parser("use", help="Select codex/local or GLM.")
    use_parser.add_argument("provider", choices=PROVIDERS)
    use_parser.add_argument("--glm-model", default=None)
    use_parser.add_argument("--glm-base-url", default=None)

    subparsers.add_parser("onboard", help="Run the first-use guided setup.")
    subparsers.add_parser("skills", help="Show built-in codbeing flows that run when relevant.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.lab_state:
        if not args.json:
            print("--lab-state requires --json", file=sys.stderr)
            return 2
        print(json.dumps({"state": _json_lab_state()}, separators=(",", ":")))
        return 0

    config = load_config(args.config)

    if args.command is None:
        return _home(config, args.config)

    if args.command == "capture":
        return _capture(args, config)
    if args.command in ("quick", "run") and args.trace_file is None:
        print(f"`cb {args.command}` validates and analyzes a DecisionTrace JSON file.")
        print(f"Usage: cb {args.command} TRACE_FILE [--reports-dir DIR] [--model MODEL]")
        return 0
    if args.command == "example":
        return _example(args, config)
    if args.command == "model":
        return _model(args, config)
    if args.command == "onboard":
        return _onboard(args.config, config)
    if args.command == "skills":
        return _skills()

    try:
        trace = _read_json(args.trace_file)
        if args.command == "validate":
            validate_decision_trace(trace)
        else:
            report = analyze_decision_traces(trace)
            report = _append_model_assist(report, trace, config, args.model)
    except FileNotFoundError:
        print(f"validation error: file not found: {args.trace_file}")
        return 2
    except json.JSONDecodeError as error:
        print(f"validation error: invalid JSON: {error.msg}")
        return 2
    except DecisionTraceValidationError as error:
        print(f"validation error: {error}")
        return 2

    if args.command == "validate":
        print(f"valid DecisionTrace: {args.trace_file}")
        return 0

    if args.command == "analyze":
        report_file = args.report_file
    else:
        report_file = _next_report_path(args.reports_dir, args.name or args.trace_file.stem)
        print(f"valid DecisionTrace input: {args.trace_file}")

    return _write_report(report_file, report)


def _json_lab_state() -> str:
    """Inspect only the isolated CODBEING_HOME capture store for JSON state."""
    home = Path(os.environ.get("CODBEING_HOME", ".codbeing"))
    captures_dir = home / "captures"
    try:
        has_capture = any(path.is_file() for path in captures_dir.glob("*.jsonl"))
    except OSError:
        has_capture = False
    return "trace_evidence" if has_capture else "empty_lab"


def _add_model_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        choices=("auto", *PROVIDERS),
        default="auto",
        help="Report execution model. auto uses saved config.",
    )


def _home(config: CodbeingConfig, config_path: Path) -> int:
    mode = "로컬 살펴보기"
    while True:
        state = _lab_state()
        summary = summarize_research_state(state)
        actions = _lab_actions(
            state.trace_count,
            state.latest_report,
            model_fixture=_lab_fixture_name() == "model",
        )
        _render_lab_entrance(
            summary,
            actions,
            config,
            config_path,
            state.trace_count,
            mode,
            state.submitted_material,
        )

        try:
            selection = input("번호를 고르세요 (q: 종료): ").strip()
        except (EOFError, OSError):
            return 0

        if selection.lower() in {"", "q", "quit", "exit"}:
            return 0
        if selection.lower() == "b":
            mode = "Solo inspect"
            continue

        action = _lab_action_from_selection(selection, actions)
        if action is None:
            _print_invalid_lab_input()
            return 2

        mode = _render_lab_surface(action, config, mode)


def _lab_state() -> ResearchState:
    fixture_name = _lab_fixture_name()
    if fixture_name == "trace":
        return _trace_fixture_state()
    if fixture_name == "report":
        return _report_fixture_state()
    if fixture_name == "evidence":
        return _evidence_fixture_state()
    if fixture_name == "model":
        return _model_fixture_state()
    return load_research_state(
        DEFAULT_TRACE_STORE,
        DEFAULT_REPORTS_DIR,
        DEFAULT_SUBMITTED_MATERIAL_STORE,
    )


def _lab_fixture_name() -> str:
    """Return the explicitly requested deterministic lab fixture, if any."""
    return os.environ.get(LAB_STATE_FIXTURE_ENV, "").strip().lower()


def _trace_fixture_state() -> ResearchState:
    """Provide deterministic local trace context without creating private files."""
    return ResearchState(
        traces=(dict(ACADEMIC_NOMUSA_TRACES[0]),),
        trace_store_has_issue=False,
        reports=(),
        latest_report=None,
        reports_directory_has_issue=False,
        submitted_material=(),
        submitted_material_store_has_issue=False,
    )


def _report_fixture_state() -> ResearchState:
    """Provide deterministic report context without reading private files."""
    report = Path("report-fixture-local-analysis.md")
    return ResearchState(
        traces=(dict(ACADEMIC_NOMUSA_TRACES[0]),),
        trace_store_has_issue=False,
        reports=(report,),
        latest_report=report,
        reports_directory_has_issue=False,
        submitted_material=(),
        submitted_material_store_has_issue=False,
    )


def _evidence_fixture_state() -> ResearchState:
    """Provide deterministic evidence and analysis context without local file access."""
    report = Path("evidence-fixture-local-analysis.md")
    return ResearchState(
        traces=tuple(dict(trace) for trace in ACADEMIC_NOMUSA_TRACES),
        trace_store_has_issue=False,
        reports=(report,),
        latest_report=report,
        reports_directory_has_issue=False,
        submitted_material=(),
        submitted_material_store_has_issue=False,
    )


def _model_fixture_state() -> ResearchState:
    """Provide deterministic local context for inspecting model boundaries."""
    report = Path("model-fixture-local-analysis.md")
    return ResearchState(
        traces=(dict(ACADEMIC_NOMUSA_TRACES[0]),),
        trace_store_has_issue=False,
        reports=(report,),
        latest_report=report,
        reports_directory_has_issue=False,
        submitted_material=(),
        submitted_material_store_has_issue=False,
    )


def _lab_actions(
    trace_count: int, latest_report: Path | None, model_fixture: bool = False
) -> list[tuple[str, str]]:
    del trace_count, latest_report, model_fixture
    return [
        ("demo", "노무사 예시로 시작하기 (Nomusa 데모)"),
        ("capture", "내 결정 기록하기 (기록/캡처)"),
        ("analysis", "저장된 기록 분석 보기"),
        ("model-boundary", "모델·개인정보 상태 확인"),
    ]


def _render_lab_entrance(
    summary: ResearchStateSummary,
    actions: Sequence[tuple[str, str]],
    config: CodbeingConfig,
    config_path: Path,
    trace_count: int,
    mode: str = "Solo inspect",
    submitted_material: Sequence[str] = (),
) -> None:
    """Render the local research state and its currently meaningful actions."""
    del config_path, trace_count, mode, submitted_material
    print("코드빙 연구실 (codbeing Lab)")
    print("내 기록을 이 기기 안에서 정리하고 살펴보는 개인 연구실입니다.")
    print("기본값은 로컬 전용입니다. API 키 없이도 기록과 분석을 사용할 수 있습니다.")
    print("외부 모델(GLM 등)은 직접 선택하고 키가 준비된 경우에만 사용합니다.")
    print("이 화면은 비밀값, API 키, 원문 개인 기록을 출력하지 않습니다.")
    print("")
    print("처음 할 일:")
    for index, (_, label) in enumerate(actions, start=1):
        print(f"  {index}. {label}")
    print("")
    print(f"현재 로컬 상태: 기록 {summary.evidence} / 분석 {summary.analysis}")
    print(
        "고급 명령어도 그대로 사용할 수 있습니다: capture, run, quick, model, "
        "example nomusa, skills, cb onboard, cb model status."
    )


def _render_submitted_material_context(submitted_material: Sequence[str]) -> None:
    if not submitted_material:
        print("Submitted material: no local notes yet")
        return

    latest_material = submitted_material[-1]
    preview = latest_material if len(latest_material) <= 140 else f"{latest_material[:137]}..."
    noun = "note" if len(submitted_material) == 1 else "notes"
    print(f"Submitted material: {len(submitted_material)} local {noun}; latest: {preview}")


def _render_empty_lab_entrance() -> None:
    """Render the privacy-preserving first screen for an empty lab."""
    print("Codbeing Lab")
    print("Private research lab - local solo mode")
    print("No material, traces, reports, models, or evidence yet.")
    print(
        "Model assist: off. Nothing leaves this machine unless you explicitly select a model and a key is available."
    )
    print("1. Talk with researcher")
    print("2. Submit material")
    print("3. Receive experiment/question")
    print("4. Solo inspect")
    print("5. Researcher accompaniment")
    print("q. Quit")


def _run_lab_action(actions: list[tuple[str, str]], config: CodbeingConfig) -> int:
    try:
        selection = input("Choose an action, press Enter to leave, or q to quit: ").strip()
    except (EOFError, OSError):
        return 0
    if selection.lower() in {"", "q", "quit", "exit"}:
        return 0
    action = _lab_action_from_selection(selection, actions)
    if action is None:
        _print_invalid_lab_input()
        return 2

    _render_lab_surface(action, config, "Solo inspect")
    return 0


def _lab_action_from_selection(
    selection: str, actions: Sequence[tuple[str, str]]
) -> str | None:
    shortcuts = {
        "r": "accompany",
        "s": "solo",
        "e": "evidence",
        "5": "apparatus",
        "6": "solo",
    }
    shortcut_action = shortcuts.get(selection.lower())
    if shortcut_action is not None:
        return shortcut_action

    try:
        action_index = int(selection) - 1
        if action_index < 0:
            raise ValueError
        return actions[action_index][0]
    except (ValueError, IndexError):
        return None


def _print_invalid_lab_input() -> None:
    print(
        "입력이 올바르지 않습니다. 번호를 고르거나 q를 입력해 종료하세요.",
        file=sys.stderr,
    )


def _render_lab_surface(action: str, config: CodbeingConfig, mode: str) -> str:
    """Render a local surface and return the session mode for the next entrance."""
    if action == "demo":
        print("노무사 예시를 로컬에 준비하고 분석합니다. 외부 모델은 사용하지 않습니다.")
        _example(
            argparse.Namespace(
                example_name="nomusa",
                trace_file=Path("private-traces/academic-nomusa.json"),
                reports_dir=DEFAULT_REPORTS_DIR,
                name="academic-nomusa",
                model="codex",
            ),
            config,
        )
        return mode
    elif action == "capture":
        print("내 기록을 이 기기에만 저장합니다. 먼저 짧은 메모를 남길 수 있습니다.")
        return _render_lab_surface("submit", config, mode)
    elif action == "accompany":
        print("Surface: Researcher accompaniment")
        print("Mode: Researcher accompaniment")
        print("Researcher accompaniment is optional and begins with local reflection.")
        print("LLM assist requires explicit model selection and key availability; no material is sent automatically.")
        print("Enter b for the lab entrance or 6 to Return to solo.")
        return "Researcher accompaniment"

    if action == "submit":
        print("Surface: Submit material")
        print("Material stays private and local here; no model is selected or called.")
        try:
            material = input("Submit local material (blank skips saving): ").strip()
        except (EOFError, OSError):
            print("No material submitted.")
        else:
            if not material:
                print("No material submitted.")
            else:
                try:
                    material_count = append_submitted_material(
                        DEFAULT_SUBMITTED_MATERIAL_STORE, material
                    )
                except (OSError, ValueError) as error:
                    print(f"Local material error: {error}")
                else:
                    print(f"Submitted material saved locally. Local note count: {material_count}")
                    print("It will appear in later entrance and evidence context.")
    elif action == "evidence":
        print("Surface: Evidence")
        print(f"Evidence ledger: {DEFAULT_TRACE_STORE}")
        state = _lab_state()
        print(f"Stored DecisionTraces: {state.trace_count}")
        _render_submitted_material_context(state.submitted_material)
        if state.trace_count:
            print("Evidence status: stored DecisionTraces are available for local inspection.")
        elif state.submitted_material:
            noun = "note is" if len(state.submitted_material) == 1 else "notes are"
            print(
                f"Evidence intake: {len(state.submitted_material)} submitted local {noun} "
                "waiting for DecisionTrace capture."
            )
        else:
            print("Evidence empty: no submitted material or stored DecisionTraces yet.")
            print("Receive experiment/question offline: What changed after your last decision?")
    elif action == "analysis":
        print("Surface: Reports / analysis")
        state = _lab_state()
        latest_report = state.latest_report
        if latest_report is not None:
            print(f"Latest local report: {latest_report.name}")
            if _lab_fixture_name() in {"report", "evidence"}:
                print("# Local report fixture")
                print("DecisionTrace evidence is ready for private analysis review.")
            else:
                print(latest_report.read_text(encoding="utf-8"))
            if state.submitted_material:
                _render_submitted_material_context(state.submitted_material)
                print(
                    "Analysis context: submitted material remains local until it is captured "
                    "as evidence or included in a later local report."
                )
            elif state.trace_count:
                print(
                    f"Analysis context: this local report can be inspected alongside "
                    f"{state.trace_count} stored DecisionTrace"
                    f"{'s' if state.trace_count != 1 else ''}."
                )
        else:
            if state.submitted_material:
                _render_submitted_material_context(state.submitted_material)
                print(
                    "No local reports yet. Submitted material is available for local evidence "
                    "intake, but has not been analyzed."
                )
                print("Local next step: capture a DecisionTrace to generate a report.")
            elif state.trace_count:
                print(
                    f"No local reports yet. {state.trace_count} stored DecisionTrace"
                    f"{'s are' if state.trace_count != 1 else ' is'} available for local analysis."
                )
            else:
                print(
                    "Analysis empty: no submitted material, stored DecisionTraces, or local reports yet."
                )
                print("Receive experiment/question offline: What changed after your last decision?")
    elif action == "apparatus":
        state = _lab_state()
        trace_count = state.trace_count
        print("Surface: Self Code and Simulation")
        if trace_count:
            print(f"Self Code lens: {trace_count} stored DecisionTraces reveal repeated local patterns.")
        elif state.submitted_material:
            _render_submitted_material_context(state.submitted_material)
            noun = "note is" if len(state.submitted_material) == 1 else "notes are"
            print(
                f"Self Code intake: {len(state.submitted_material)} submitted local {noun} "
                "available for private pattern review after DecisionTrace capture."
            )
        else:
            print("Self Code empty: no submitted material or stored DecisionTraces yet.")
            print("Submit local material before inferring repeated patterns.")
        _render_simulation_context(state)
    elif action == "model-boundary":
        print("모델·개인정보 경계")
        print("기본 분석은 로컬에서만 실행되며 LLM API 키가 없어도 사용할 수 있습니다.")
        print("외부 모델(GLM 등)은 사용자가 직접 선택하고 키가 있을 때만 보조 기능으로 요청됩니다.")
        print("개인 기록, 분석 보고서, 비밀값은 자동으로 외부에 전송되지 않습니다.")
        print("선택된 모델은 필요할 때 `cb model status`로 확인할 수 있습니다.")
    elif action == "solo":
        print("Surface: Return to solo")
        print("Mode: Solo inspect")
        print("Solo inspect remains local. No external model is selected or called here.")
        return "Solo inspect"
    else:
        raise ValueError(f"Unsupported lab action: {action}")

    print("번호를 다시 고르거나 q를 입력해 종료하세요.")
    return mode


def _render_simulation_context(state: ResearchState) -> None:
    """Render only the local material that can ground a branch rehearsal."""
    if state.submitted_material:
        noun = "note can" if len(state.submitted_material) == 1 else "notes can"
        print(
            f"Simulation input: {len(state.submitted_material)} submitted local {noun} "
            "anchor a private branch rehearsal."
        )
        print("Local branch prompt: What would you try differently before the next decision?")
    elif state.trace_count:
        print(
            f"Simulation evidence: {state.trace_count} stored DecisionTrace"
            f"{'s can' if state.trace_count != 1 else ' can'} ground a local branch comparison."
        )
    else:
        print("Simulation empty: no submitted material or stored DecisionTraces yet.")
        print("Receive experiment/question offline: What could you try before your next decision?")

    if state.latest_report is not None:
        print(f"Simulation report context: compare branches against local report {state.latest_report.name}.")


def _capture(args: argparse.Namespace, config: CodbeingConfig) -> int:
    try:
        trace = _prompt_for_trace()
        validate_decision_trace(trace)
        traces = _load_trace_store(args.store)
        traces.append(trace)
        _write_json(args.store, traces)
    except EOFError:
        print("Capture needs interactive input. Re-run `cb capture` in a terminal to record a DecisionTrace.")
        return 0
    except (json.JSONDecodeError, DecisionTraceValidationError) as error:
        print(f"capture error: {error}")
        return 2

    print(f"DecisionTrace appended: {args.store}")
    print(f"Trace count: {len(traces)}")

    if args.no_analyze:
        return 0

    report = analyze_decision_traces(traces)
    report = _append_model_assist(report, traces, config, args.model)
    report_file = _next_report_path(args.reports_dir, args.name or args.store.stem)
    return _write_report(report_file, report)


def _example(args: argparse.Namespace, config: CodbeingConfig) -> int:
    if args.example_name != "nomusa":
        print(f"example error: unsupported example: {args.example_name}")
        return 2
    if args.trace_file.exists():
        try:
            existing_traces = _read_json(args.trace_file)
        except (OSError, json.JSONDecodeError):
            existing_traces = None
        if existing_traces != ACADEMIC_NOMUSA_TRACES:
            print(f"output error: trace file already exists: {args.trace_file}")
            return 2
        print(f"Example DecisionTrace already present: {args.trace_file}")
    else:
        _write_json(args.trace_file, ACADEMIC_NOMUSA_TRACES)
        print(f"Example DecisionTrace written: {args.trace_file}")

    report = analyze_decision_traces(ACADEMIC_NOMUSA_TRACES)
    report = _append_model_assist(report, ACADEMIC_NOMUSA_TRACES, config, args.model)
    report_file = _next_report_path(args.reports_dir, args.name)
    return _write_report(report_file, report)


def _model(args: argparse.Namespace, config: CodbeingConfig) -> int:
    if args.model_command is None:
        print("Model configuration")
        _print_model_status(config)
        print("Use `cb model use codex` or `cb model use glm` to select a report model.")
        return 0

    if args.model_command == "status":
        _print_model_status(config)
        return 0

    updated = CodbeingConfig(
        model_provider=args.provider,
        glm_model=args.glm_model or config.glm_model,
        glm_base_url=args.glm_base_url or config.glm_base_url,
    )
    save_config(updated, args.config)
    print(f"Model set: {updated.model_provider}")
    print(f"Config written: {args.config}")
    _print_model_status(updated)
    return 0


def _onboard(config_path: Path, config: CodbeingConfig) -> int:
    print("codbeing onboarding")
    print("")
    print("1. Choose the default model.")
    print("   - codex: local evidence-grounded report only; no external trace upload.")
    print("   - glm: call GLM for an optional review when an API key exists.")
    provider = _ask("Default model: codex/glm", default=config.model_provider).lower()
    if provider not in PROVIDERS:
        print("onboard error: model must be codex or glm")
        return 2

    updated = CodbeingConfig(
        model_provider=provider,
        glm_model=_ask("GLM model", default=config.glm_model),
        glm_base_url=_ask("GLM base URL", default=config.glm_base_url),
    )
    save_config(updated, config_path)
    print(f"Config written: {config_path}")
    print("")
    print("2. Use these next:")
    print("   cb capture")
    print("   cb run private-traces/decision-traces.json")
    print("   cb example nomusa")
    print("")
    _skills()
    return 0


def _print_model_status(config: CodbeingConfig) -> None:
    summary = config_summary(config)
    print("Model status")
    print(f"- provider: {summary['model_provider']}")
    print(f"- glm_model: {summary['glm_model']}")
    print(f"- glm_base_url: {summary['glm_base_url']}")
    print(f"- glm_api_key_present: {summary['glm_api_key_present']}")
    print(f"- glm_anthropic_compatible_env_present: {summary['glm_anthropic_compatible_env_present']}")
    print("- Boundary: `cb model` only reads or saves local configuration; it sends no research material.")
    print(
        "- External LLM assist requires an explicit `--model glm` request, "
        "a configured model and key, and confirmation before private material is sent."
    )


def _skills() -> int:
    print("Built-in codbeing flows")
    print("- capture: asks DecisionTrace questions, appends locally, then analyzes.")
    print("- run/quick: validates a trace file and writes a numbered local report.")
    print("- example nomusa: creates the academic/Nomusa dogfooding fixture.")
    print("- hard mirror gate: runs automatically when impact, reversibility, pressure, confidence, and activation-pattern fields are present.")
    print("- model assist: uses codex/local by default; GLM only when selected and an API key is present.")
    return 0


def _prompt_for_trace() -> dict[str, Any]:
    print("Capture one DecisionTrace. Leave optional privacy fields blank to skip.")
    trace = {
        "context": _ask("Context"),
        "options": _ask_list("Options, comma-separated"),
        "chosen_action": _ask("Chosen action"),
        "rejected_options": _ask_list("Rejected options, comma-separated"),
        "judgment_basis": _ask("Judgment basis"),
        "observed_behavior": _ask("Observed behavior"),
        "outcome": _ask("Outcome"),
        "aftertaste": _ask("Aftertaste"),
        "memory_confidence": _ask("Memory confidence", default="medium"),
        "source": _ask("Source", default="interactive capture"),
    }
    privacy_level = _ask("Privacy level", default="")
    redaction_notes = _ask("Redaction notes", default="")
    if privacy_level:
        trace["privacy_level"] = privacy_level
    if redaction_notes:
        trace["redaction_notes"] = redaction_notes
    return trace


def _ask(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    return ""


def _ask_list(label: str) -> list[str]:
    value = _ask(label)
    return [item.strip() for item in value.split(",") if item.strip()]


def _load_trace_store(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = _read_json(path)
    if isinstance(payload, dict):
        validate_decision_trace(payload)
        return [payload]
    if isinstance(payload, list):
        for trace in payload:
            validate_decision_trace(trace)
        return payload
    raise DecisionTraceValidationError(
        "trace store must be one DecisionTrace object or an array of DecisionTrace objects."
    )


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as trace_handle:
        return json.load(trace_handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_report(report_file: Path, report: str) -> int:
    if report_file.exists():
        print(f"output error: report file already exists: {report_file}")
        return 2
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report, encoding="utf-8")
    print(f"Runtime Analysis report written: {report_file}")
    return 0


def _next_report_path(reports_dir: Path, stem: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = _safe_filename_stem(stem)
    suffix = 1
    candidate = reports_dir / f"{safe_stem}-runtime-analysis-{suffix}.md"
    while candidate.exists():
        suffix += 1
        candidate = reports_dir / f"{safe_stem}-runtime-analysis-{suffix}.md"
    return candidate


def _safe_filename_stem(stem: str) -> str:
    safe = "".join(character if character.isalnum() or character in "-_" else "-" for character in stem)
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "decision-trace"


def _append_model_assist(
    report: str,
    payload: Any,
    config: CodbeingConfig,
    provider_override: str | None,
) -> str:
    provider = resolve_provider(config, provider_override)
    traces = payload if isinstance(payload, list) else [payload]
    assist_requested = provider_override == "glm"
    consent_granted = False
    if assist_requested and external_assist_ready(config, provider):
        consent_granted = _confirm_external_context_sharing()
    section = model_assist_section(
        traces,
        report,
        config,
        provider,
        consent_granted=consent_granted,
        assist_requested=assist_requested,
    )
    return report.rstrip() + "\n\n" + "\n".join(section)


def _confirm_external_context_sharing() -> bool:
    """Ask before an external provider receives raw research material."""
    response = input(
        "External LLM assist will receive the full DecisionTrace and report body. "
        "Send this private material externally? [y/N]: "
    )
    return response.strip().lower() in {"y", "yes"}


if __name__ == "__main__":
    raise SystemExit(main())
