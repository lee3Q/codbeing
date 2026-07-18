"""Focused coverage for the no-arguments codbeing lab entrance."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from codbeing.__main__ import (
    _append_model_assist,
    _home,
    _lab_actions,
    _render_lab_entrance,
    _run_lab_action,
    main,
)
from codbeing.config import CodbeingConfig
from codbeing.lab_state import ResearchStateSummary


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


class LabLauncherTests(unittest.TestCase):
    def test_cb_no_args_renders_lab_without_stderr(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            input="\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("코드빙 연구실", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_no_args_lab_uses_four_korean_first_actions_and_local_privacy_copy(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            input="q\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("처음 할 일:", result.stdout)
        self.assertIn("1. 노무사 예시로 시작하기", result.stdout)
        self.assertIn("2. 내 결정 기록하기", result.stdout)
        self.assertIn("3. 저장된 기록 분석 보기", result.stdout)
        self.assertIn("4. 모델·개인정보 상태 확인", result.stdout)
        self.assertIn("기본값은 로컬 전용입니다.", result.stdout)
        self.assertIn("API 키 없이도 기록과 분석을 사용할 수 있습니다.", result.stdout)
        self.assertIn("외부 모델(GLM 등)은 직접 선택", result.stdout)
        self.assertIn("비밀값, API 키, 원문 개인 기록을 출력하지 않습니다.", result.stdout)

    def test_interactive_lab_exits_cleanly_for_blank_quit_or_closed_input(self) -> None:
        actions = _lab_actions(0, None)

        with patch("builtins.input", return_value="") as prompt:
            _run_lab_action(actions, CodbeingConfig())
        prompt.assert_called_once()

        with patch("builtins.input", side_effect=EOFError):
            _run_lab_action(actions, CodbeingConfig())

    def test_invalid_lab_input_returns_nonzero_and_reports_actionable_error(self) -> None:
        actions = _lab_actions(0, None)
        stderr = io.StringIO()

        with patch("builtins.input", return_value="not-a-choice"), redirect_stderr(stderr):
            result = _run_lab_action(actions, CodbeingConfig())

        self.assertEqual(result, 2)
        self.assertIn("입력이 올바르지 않습니다", stderr.getvalue())

        with patch("builtins.input", return_value="q"):
            _run_lab_action(actions, CodbeingConfig())

    def test_cb_no_args_accepts_piped_quit(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            input="q\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("코드빙 연구실", result.stdout)
        self.assertIn("q: 종료", result.stdout)
        self.assertNotIn("project picker", result.stdout.lower())
        self.assertNotIn("new research", result.stdout.lower())
        self.assertNotIn("continue research", result.stdout.lower())

    def test_every_no_args_lab_state_avoids_project_oriented_language(self) -> None:
        forbidden_labels = ("project picker", "new research", "continue research")

        for fixture_name in ("", "trace", "report", "evidence", "model"):
            with self.subTest(fixture_name=fixture_name or "empty"):
                environment = os.environ.copy()
                environment["CODBEING_DISABLE_SHELL_KEY_LOOKUP"] = "1"
                if fixture_name:
                    environment["CODBEING_LAB_STATE_FIXTURE"] = fixture_name
                else:
                    environment.pop("CODBEING_LAB_STATE_FIXTURE", None)

                result = subprocess.run(
                    [sys.executable, "-m", "codbeing"],
                    capture_output=True,
                    check=False,
                    cwd=Path(__file__).parents[1],
                    env=environment,
                    input="q\n",
                    text=True,
                )

                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                output = result.stdout.lower()
                for label in forbidden_labels:
                    self.assertNotIn(label, output)

    def test_trace_fixture_renders_trace_actions_and_local_model_boundary(self) -> None:
        environment = os.environ.copy()
        environment["CODBEING_LAB_STATE_FIXTURE"] = "trace"
        environment["CODBEING_DISABLE_SHELL_KEY_LOOKUP"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            env=environment,
            input="q\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("코드빙 연구실", result.stdout)
        self.assertIn("저장된 기록 분석 보기", result.stdout)
        self.assertIn("모델·개인정보 상태 확인", result.stdout)
        self.assertIn("기본값은 로컬 전용입니다.", result.stdout)

    def test_report_fixture_renders_analysis_context_and_global_lab_controls(self) -> None:
        environment = os.environ.copy()
        environment["CODBEING_LAB_STATE_FIXTURE"] = "report"
        environment["CODBEING_DISABLE_SHELL_KEY_LOOKUP"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            env=environment,
            input="r\ns\n3\nq\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("코드빙 연구실", result.stdout)
        self.assertIn("저장된 기록 분석 보기", result.stdout)
        self.assertIn("Surface: Reports / analysis", result.stdout)
        self.assertIn("# Local report fixture", result.stdout)
        self.assertIn("Analysis context: this local report can be inspected alongside 1 stored DecisionTrace.", result.stdout)
        self.assertIn("Surface: Researcher accompaniment", result.stdout)
        self.assertIn("Surface: Return to solo", result.stdout)
        self.assertIn("Mode: Solo inspect", result.stdout)
        self.assertIn(
            "외부 모델(GLM 등)은 직접 선택하고 키가 준비된 경우에만 사용합니다.",
            result.stdout,
        )

    def test_evidence_fixture_renders_evidence_lenses_and_global_controls(self) -> None:
        environment = os.environ.copy()
        environment["CODBEING_LAB_STATE_FIXTURE"] = "evidence"
        environment["CODBEING_DISABLE_SHELL_KEY_LOOKUP"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            env=environment,
            input="e\n3\n5\nr\ns\nq\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("코드빙 연구실", result.stdout)
        self.assertIn("현재 로컬 상태", result.stdout)
        self.assertIn("Surface: Evidence", result.stdout)
        self.assertIn("Stored DecisionTraces: 2", result.stdout)
        self.assertIn("Surface: Reports / analysis", result.stdout)
        self.assertIn("Surface: Self Code and Simulation", result.stdout)
        self.assertIn("Simulation evidence: 2 stored DecisionTraces can ground a local branch comparison.", result.stdout)
        self.assertIn("Surface: Researcher accompaniment", result.stdout)
        self.assertIn("Surface: Return to solo", result.stdout)
        self.assertIn("기본값은 로컬 전용입니다.", result.stdout)
        self.assertNotIn("project picker", result.stdout.lower())
        self.assertNotIn("new research", result.stdout.lower())
        self.assertNotIn("continue research", result.stdout.lower())

    def test_model_fixture_renders_explicit_assist_boundary_and_global_controls(self) -> None:
        environment = os.environ.copy()
        environment["CODBEING_LAB_STATE_FIXTURE"] = "model"
        environment["CODBEING_DISABLE_SHELL_KEY_LOOKUP"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "codbeing"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            env=environment,
            input="4\nr\ns\nq\n",
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("모델·개인정보 경계", result.stdout)
        self.assertIn("LLM API 키가 없어도 사용할 수 있습니다.", result.stdout)
        self.assertIn("외부 모델(GLM 등)은 사용자가 직접 선택", result.stdout)
        self.assertIn("개인 기록, 분석 보고서, 비밀값은 자동으로 외부에 전송되지 않습니다.", result.stdout)
        self.assertIn("Surface: Researcher accompaniment", result.stdout)
        self.assertIn("Surface: Return to solo", result.stdout)
        self.assertIn("Mode: Solo inspect", result.stdout)

    def test_cb_no_args_stdout_is_deterministic_for_identical_input(self) -> None:
        command = [sys.executable, "-m", "codbeing"]
        results = [
            subprocess.run(
                command,
                capture_output=True,
                check=False,
                cwd=Path(__file__).parents[1],
                input="q\n",
                text=True,
            )
            for _ in range(2)
        ]

        self.assertEqual([result.returncode for result in results], [0, 0])
        self.assertEqual(results[0].stdout, results[1].stdout)
        self.assertEqual(results[0].stderr, results[1].stderr)

    def test_populated_lab_stdout_is_deterministic_for_identical_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            trace_store = workspace / "private-traces" / "decision-traces.json"
            trace_store.parent.mkdir()
            trace_store.write_text(json.dumps([TRACE]), encoding="utf-8")
            reports_directory = workspace / "private-reports"
            reports_directory.mkdir()
            report = reports_directory / "latest.md"
            report.write_text("# Local analysis\n", encoding="utf-8")
            os.utime(report, (1, 1))

            outputs = [self._run_in_workspace(workspace) for _ in range(2)]

        self.assertEqual(outputs[0], outputs[1])
        self.assertNotRegex(outputs[0], r"\b20\d{2}-\d{2}-\d{2}\b")

    def test_home_starts_interactive_prompt_for_terminal_sessions(self) -> None:
        with (
            patch("codbeing.__main__.sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="") as prompt,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                _home(CodbeingConfig(), Path("private/codbeing-config.json")), 0
            )

        prompt.assert_called_once()

    def test_cli_routes_no_args_to_lab_and_power_commands_away_from_it(self) -> None:
        config = CodbeingConfig()

        with (
            patch("codbeing.__main__.load_config", return_value=config),
            patch("codbeing.__main__._home", return_value=0) as home,
        ):
            self.assertEqual(main([]), 0)

        home.assert_called_once()

        with (
            patch("codbeing.__main__.load_config", return_value=config),
            patch("codbeing.__main__._home", return_value=0) as home,
            patch("codbeing.__main__._capture", return_value=0) as capture,
            patch("codbeing.__main__._model", return_value=0) as model,
            patch("codbeing.__main__._example", return_value=0) as example,
            patch("codbeing.__main__._skills", return_value=0) as skills,
            patch("codbeing.__main__._read_json", return_value=TRACE),
            patch("codbeing.__main__.analyze_decision_traces", return_value="# Report"),
            patch("codbeing.__main__._append_model_assist", return_value="# Report"),
            patch("codbeing.__main__._write_report", return_value=0) as write_report,
        ):
            self.assertEqual(main(["capture"]), 0)
            self.assertEqual(main(["quick"]), 0)
            self.assertEqual(main(["run", "trace.json"]), 0)
            self.assertEqual(main(["model", "status"]), 0)
            self.assertEqual(main(["example", "nomusa"]), 0)
            self.assertEqual(main(["skills"]), 0)

        home.assert_not_called()
        capture.assert_called_once()
        model.assert_called_once()
        example.assert_called_once()
        skills.assert_called_once()
        write_report.assert_called_once()

    def test_cb_skills_keeps_its_legacy_flow_listing(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "codbeing", "skills"],
            capture_output=True,
            check=False,
            cwd=Path(__file__).parents[1],
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Built-in codbeing flows", result.stdout)
        self.assertIn("capture: asks DecisionTrace questions", result.stdout)
        self.assertIn("run/quick: validates a trace file", result.stdout)
        self.assertIn("example nomusa: creates", result.stdout)
        self.assertIn("model assist: uses codex/local by default", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_lab_entry_and_local_exploration_do_not_start_model_assist(self) -> None:
        with patch("codbeing.__main__.model_assist_section") as model_assist:
            self._run_in_empty_workspace()
            actions = _lab_actions(1, Path("private-reports/latest.md"))
            with patch("builtins.input", side_effect=["2", ""]):
                _run_lab_action(actions, CodbeingConfig(model_provider="glm"))
            for selection in ("3", "4"):
                with patch("builtins.input", return_value=selection):
                    _run_lab_action(actions, CodbeingConfig(model_provider="glm"))

        model_assist.assert_not_called()

    def test_default_lab_does_not_enter_external_assist_flow(self) -> None:
        with (
            patch("codbeing.__main__.external_assist_ready") as external_assist_ready,
            patch("codbeing.__main__._confirm_external_context_sharing") as confirm_sharing,
            patch("codbeing.models._call_glm") as call_glm,
        ):
            output = self._run_in_empty_workspace()

        self.assertIn("코드빙 연구실", output)
        external_assist_ready.assert_not_called()
        confirm_sharing.assert_not_called()
        call_glm.assert_not_called()

    def test_explicit_analysis_command_starts_model_assist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            trace_path = workspace / "trace.json"
            report_path = workspace / "report.md"
            trace_path.write_text(json.dumps(TRACE), encoding="utf-8")

            with (
                patch(
                    "codbeing.__main__.model_assist_section", return_value=["## Model Assist"]
                ) as model_assist,
                patch("codbeing.__main__.external_assist_ready", return_value=False),
            ):
                result = main(
                    [
                        "analyze",
                        str(trace_path),
                        str(report_path),
                        "--model",
                        "glm",
                    ]
                )

        self.assertEqual(result, 0)
        model_assist.assert_called_once()

    def test_saved_glm_config_does_not_request_assist_without_model_action(self) -> None:
        config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

        with (
            patch("codbeing.__main__.external_assist_ready") as external_assist_ready,
            patch("codbeing.__main__._confirm_external_context_sharing") as confirm_sharing,
            patch("codbeing.__main__.model_assist_section", return_value=["## Model Assist"])
            as model_assist,
        ):
            _append_model_assist("# Local report", TRACE, config, "auto")

        external_assist_ready.assert_not_called()
        confirm_sharing.assert_not_called()
        self.assertFalse(model_assist.call_args.kwargs["assist_requested"])

    def test_empty_lab_offers_first_contact_without_subcommands(self) -> None:
        output = self._run_in_empty_workspace()

        self.assertIn("코드빙 연구실", output)
        self.assertIn("처음 할 일:", output)
        self.assertIn("노무사 예시로 시작하기", output)
        self.assertIn("내 결정 기록하기", output)
        self.assertIn("저장된 기록 분석 보기", output)
        self.assertIn("모델·개인정보 상태 확인", output)

    def test_entrance_renders_state_meaningful_navigation_surfaces(self) -> None:
        empty_summary = ResearchStateSummary(
            evidence="no submitted DecisionTraces yet",
            analysis="no local reports yet",
            apparatus=("Evidence",),
            warnings=(),
        )
        empty_actions = _lab_actions(0, None)
        populated_actions = _lab_actions(2, Path("private-reports/latest.md"))

        empty_output = self._render_entrance(empty_summary, empty_actions, trace_count=0)
        populated_output = self._render_entrance(
            ResearchStateSummary(
                evidence="2 stored DecisionTraces",
                analysis="latest local report is latest.md",
                apparatus=("Evidence", "Self Code", "Analysis"),
                warnings=(),
            ),
            populated_actions,
            trace_count=2,
        )

        for output in (empty_output, populated_output):
            self.assertIn("처음 할 일:", output)
            self.assertIn("1. 노무사 예시로 시작하기", output)
            self.assertIn("2. 내 결정 기록하기", output)
            self.assertIn("3. 저장된 기록 분석 보기", output)
            self.assertIn("4. 모델·개인정보 상태 확인", output)

    def test_lab_reflects_saved_evidence_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            trace_store = workspace / "private-traces" / "decision-traces.json"
            trace_store.parent.mkdir()
            trace_store.write_text(json.dumps([TRACE, TRACE]), encoding="utf-8")
            reports_directory = workspace / "private-reports"
            reports_directory.mkdir()
            (reports_directory / "latest.md").write_text("# Local analysis\n", encoding="utf-8")

            output = self._run_in_workspace(workspace)

        self.assertIn("코드빙 연구실", output)
        self.assertIn("현재 로컬 상태: 기록 2 stored DecisionTraces", output)
        self.assertIn("분석 latest local report is latest.md", output)

    def test_lab_navigation_keeps_mode_and_returns_to_solo(self) -> None:
        output = io.StringIO()

        with patch("builtins.input", side_effect=["r", "b", "5", "s", "q"]), redirect_stdout(output):
            self.assertEqual(_home(CodbeingConfig(), Path("private/codbeing-config.json")), 0)

        rendered = output.getvalue()
        self.assertIn("Surface: Researcher accompaniment", rendered)
        self.assertIn("Mode: Researcher accompaniment", rendered)
        self.assertIn("Surface: Self Code and Simulation", rendered)
        self.assertIn("Surface: Return to solo", rendered)
        self.assertIn("Mode: Solo inspect", rendered)

    def test_lab_shortcuts_toggle_accompaniment_and_solo_state(self) -> None:
        output = io.StringIO()

        with patch("builtins.input", side_effect=["r", "s", "e", "b", "q"]), redirect_stdout(output):
            self.assertEqual(_home(CodbeingConfig(), Path("private/codbeing-config.json")), 0)

        rendered = output.getvalue()
        self.assertIn("Surface: Researcher accompaniment", rendered)
        self.assertIn("Surface: Return to solo", rendered)
        self.assertIn("Surface: Evidence", rendered)
        self.assertIn("기본값은 로컬 전용입니다.", rendered)

    def test_evidence_surface_distinguishes_empty_and_submitted_local_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            original_directory = Path.cwd()
            empty_output = io.StringIO()
            submitted_output = io.StringIO()
            try:
                os.chdir(workspace)
                with (
                    patch("builtins.input", side_effect=["e", "q"]),
                    redirect_stdout(empty_output),
                ):
                    self.assertEqual(main([]), 0)

                with (
                    patch("builtins.input", side_effect=["2", "A local observation.", "e", "q"]),
                    redirect_stdout(submitted_output),
                ):
                    self.assertEqual(main([]), 0)
            finally:
                os.chdir(original_directory)

        self.assertIn("Evidence empty: no submitted material or stored DecisionTraces yet.", empty_output.getvalue())
        self.assertIn(
            "Receive experiment/question offline: What changed after your last decision?",
            empty_output.getvalue(),
        )
        self.assertIn("Submitted material: 1 local note; latest: A local observation.", submitted_output.getvalue())
        self.assertIn(
            "Evidence intake: 1 submitted local note is waiting for DecisionTrace capture.",
            submitted_output.getvalue(),
        )

    def test_analysis_surface_distinguishes_empty_and_submitted_local_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            original_directory = Path.cwd()
            empty_output = io.StringIO()
            submitted_output = io.StringIO()
            try:
                os.chdir(workspace)
                with (
                    patch("builtins.input", side_effect=["3", "q"]),
                    redirect_stdout(empty_output),
                ):
                    self.assertEqual(main([]), 0)

                with (
                    patch(
                        "builtins.input",
                        side_effect=["2", "A local observation.", "3", "q"],
                    ),
                    redirect_stdout(submitted_output),
                ):
                    self.assertEqual(main([]), 0)
            finally:
                os.chdir(original_directory)

        self.assertIn(
            "Analysis empty: no submitted material, stored DecisionTraces, or local reports yet.",
            empty_output.getvalue(),
        )
        self.assertIn(
            "Receive experiment/question offline: What changed after your last decision?",
            empty_output.getvalue(),
        )
        self.assertIn(
            "Submitted material: 1 local note; latest: A local observation.",
            submitted_output.getvalue(),
        )
        self.assertIn(
            "No local reports yet. Submitted material is available for local evidence intake, "
            "but has not been analyzed.",
            submitted_output.getvalue(),
        )
        self.assertIn(
            "Local next step: capture a DecisionTrace to generate a report.",
            submitted_output.getvalue(),
        )

    def test_self_code_surface_distinguishes_empty_and_submitted_local_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            original_directory = Path.cwd()
            empty_output = io.StringIO()
            submitted_output = io.StringIO()
            try:
                os.chdir(workspace)
                with (
                    patch("builtins.input", side_effect=["5", "q"]),
                    redirect_stdout(empty_output),
                ):
                    self.assertEqual(main([]), 0)

                with (
                    patch(
                        "builtins.input",
                        side_effect=["2", "A local observation.", "5", "q"],
                    ),
                    patch("codbeing.__main__.external_assist_ready") as external_assist_ready,
                    redirect_stdout(submitted_output),
                ):
                    self.assertEqual(main([]), 0)
            finally:
                os.chdir(original_directory)

        self.assertIn("Self Code empty: no submitted material or stored DecisionTraces yet.", empty_output.getvalue())
        self.assertIn(
            "Submit local material before inferring repeated patterns.",
            empty_output.getvalue(),
        )
        external_assist_ready.assert_not_called()
        self.assertIn("Submitted material: 1 local note; latest: A local observation.", submitted_output.getvalue())
        self.assertIn(
            "Self Code intake: 1 submitted local note is available for private pattern review "
            "after DecisionTrace capture.",
            submitted_output.getvalue(),
        )

    def test_simulation_surface_uses_submitted_material_or_reports_a_truthful_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            original_directory = Path.cwd()
            empty_output = io.StringIO()
            submitted_output = io.StringIO()
            try:
                os.chdir(workspace)
                with (
                    patch("builtins.input", side_effect=["5", "q"]),
                    redirect_stdout(empty_output),
                ):
                    self.assertEqual(main([]), 0)

                with (
                    patch(
                        "builtins.input",
                        side_effect=["2", "I paused before replying.", "5", "q"],
                    ),
                    patch("codbeing.__main__.external_assist_ready") as external_assist_ready,
                    redirect_stdout(submitted_output),
                ):
                    self.assertEqual(main([]), 0)
            finally:
                os.chdir(original_directory)

        self.assertIn(
            "Simulation empty: no submitted material or stored DecisionTraces yet.",
            empty_output.getvalue(),
        )
        self.assertIn(
            "Receive experiment/question offline: What could you try before your next decision?",
            empty_output.getvalue(),
        )
        external_assist_ready.assert_not_called()
        self.assertIn(
            "Submitted material: 1 local note; latest: I paused before replying.",
            submitted_output.getvalue(),
        )
        self.assertIn(
            "Simulation input: 1 submitted local note can anchor a private branch rehearsal.",
            submitted_output.getvalue(),
        )
        self.assertIn(
            "Local branch prompt: What would you try differently before the next decision?",
            submitted_output.getvalue(),
        )

    def test_submit_material_persists_and_reappears_in_local_lab_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            original_directory = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(workspace)
                with (
                    patch("builtins.input", side_effect=["2", "I paused before replying.", "e", "q"]),
                    patch("codbeing.__main__.external_assist_ready") as external_assist_ready,
                    redirect_stdout(output),
                ):
                    self.assertEqual(main([]), 0)
            finally:
                os.chdir(original_directory)

            material_store = workspace / "private-traces" / "submitted-material.json"
            self.assertEqual(json.loads(material_store.read_text(encoding="utf-8")), ["I paused before replying."])

        rendered = output.getvalue()
        external_assist_ready.assert_not_called()
        self.assertIn("Submitted material saved locally. Local note count: 1", rendered)
        self.assertIn("Submitted material: 1 local note; latest: I paused before replying.", rendered)
        self.assertIn("Surface: Evidence", rendered)

    def _run_in_empty_workspace(self) -> str:
        with tempfile.TemporaryDirectory() as temporary_directory:
            return self._run_in_workspace(Path(temporary_directory))

    def _run_in_workspace(self, workspace: Path) -> str:
        original_directory = Path.cwd()
        output = io.StringIO()
        try:
            os.chdir(workspace)
            with redirect_stdout(output):
                self.assertEqual(main([]), 0)
        finally:
            os.chdir(original_directory)
        return output.getvalue()

    def _render_entrance(
        self,
        summary: ResearchStateSummary,
        actions: list[tuple[str, str]],
        trace_count: int,
    ) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            _render_lab_entrance(
                summary,
                actions,
                CodbeingConfig(),
                Path("private/codbeing-config.json"),
                trace_count,
            )
        return output.getvalue()
