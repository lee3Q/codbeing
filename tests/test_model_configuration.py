"""Tests for the external model preflight boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from codbeing.config import CodbeingConfig
from codbeing.__main__ import _append_model_assist
from codbeing.models import _call_glm, _call_glm_anthropic_compatible, model_assist_section


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


def test_glm_assist_does_not_call_provider_without_configured_credentials() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with (
        patch("codbeing.models._glm_api_key", return_value=None),
        patch("codbeing.models._call_glm") as call_glm,
    ):
        section = model_assist_section(
            [TRACE], "# Local report", config, "glm", assist_requested=True
        )

    call_glm.assert_not_called()
    assert "GLM API key was not found" in "\n".join(section)


def test_glm_assist_does_not_call_provider_with_blank_credentials() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with (
        patch("codbeing.models._glm_api_key", return_value="   "),
        patch("codbeing.models._call_glm") as call_glm,
    ):
        section = model_assist_section(
            [TRACE],
            "# Local report",
            config,
            "glm",
            consent_granted=True,
            assist_requested=True,
        )

    call_glm.assert_not_called()
    assert "GLM API key was not found" in "\n".join(section)


def test_glm_assist_calls_provider_with_selected_model_and_credentials() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with (
        patch("codbeing.models._glm_api_key", return_value="configured-secret"),
        patch("codbeing.models._call_glm", return_value="- Evidence review") as call_glm,
    ):
        section = model_assist_section(
            [TRACE],
            "# Local report",
            config,
            "glm",
            consent_granted=True,
            assist_requested=True,
        )

    call_glm.assert_called_once_with(
        [TRACE],
        "# Local report",
        config,
        "configured-secret",
        consent_granted=True,
        assist_requested=True,
    )
    assert "Selected model: **GLM (glm-test)**" in "\n".join(section)
    assert "GLM returned an evidence-bound review" in "\n".join(section)


def test_glm_assist_blocks_external_request_when_consent_is_denied() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with (
        patch("codbeing.models._glm_api_key", return_value="configured-secret"),
        patch("codbeing.models._call_glm") as call_glm,
    ):
        section = model_assist_section(
            [TRACE],
            "# Local report",
            config,
            "glm",
            consent_granted=False,
            assist_requested=True,
        )

    call_glm.assert_not_called()
    assert "consent to send the full DecisionTrace and report body was not granted" in "\n".join(
        section
    )


def test_raw_evidence_cannot_reach_outbound_client_without_explicit_consent() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with patch("urllib.request.urlopen") as open_url:
        try:
            _call_glm(
                [TRACE],
                "# Local report",
                config,
                "configured-secret",
                consent_granted=False,
                assist_requested=True,
            )
        except PermissionError as error:
            assert "Explicit consent is required" in str(error)
        else:
            raise AssertionError("Expected outbound raw evidence to require consent")

    open_url.assert_not_called()


def test_raw_evidence_cannot_reach_outbound_client_without_explicit_assist_action() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with patch("urllib.request.urlopen") as open_url:
        try:
            _call_glm(
                [TRACE],
                "# Local report",
                config,
                "configured-secret",
                consent_granted=True,
            )
        except PermissionError as error:
            assert "explicit LLM assist action" in str(error)
        else:
            raise AssertionError("Expected outbound raw evidence to require an assist action")

    open_url.assert_not_called()


def test_anthropic_compatible_transport_requires_explicit_consent() -> None:
    runtime_env = {
        "ANTHROPIC_BASE_URL": "https://provider.example",
        "ANTHROPIC_AUTH_TOKEN": "configured-secret",
    }

    with patch("urllib.request.urlopen") as open_url:
        try:
            _call_glm_anthropic_compatible(
                "Full raw DecisionTrace and report body",
                runtime_env,
                consent_granted=False,
                assist_requested=True,
            )
        except PermissionError as error:
            assert "Explicit consent is required" in str(error)
        else:
            raise AssertionError("Expected Anthropic-compatible outbound transport to require consent")

    open_url.assert_not_called()


def test_anthropic_compatible_transport_sends_full_body_after_consent() -> None:
    runtime_env = {
        "ANTHROPIC_BASE_URL": "https://provider.example",
        "ANTHROPIC_AUTH_TOKEN": "configured-secret",
        "ANTHROPIC_MODEL": "glm-test",
    }
    raw_body = "Full raw DecisionTrace and report body"
    response = MagicMock()
    response.read.return_value = b'{"content": [{"text": "- Evidence review"}]}'

    with patch("urllib.request.urlopen") as open_url:
        open_url.return_value.__enter__.return_value = response
        review = _call_glm_anthropic_compatible(
            raw_body,
            runtime_env,
            consent_granted=True,
            assist_requested=True,
        )

    request = open_url.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["messages"][0]["content"] == raw_body
    assert review == "- Evidence review"


def test_glm_assist_does_not_call_provider_without_explicit_assist_action() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with (
        patch("codbeing.models._glm_api_key", return_value="configured-secret"),
        patch("codbeing.models._call_glm") as call_glm,
    ):
        section = model_assist_section(
            [TRACE], "# Local report", config, "glm", consent_granted=True
        )

    call_glm.assert_not_called()
    assert "no explicit LLM assist action was requested" in "\n".join(section)


def test_local_model_never_requests_external_assist() -> None:
    config = CodbeingConfig(model_provider="codex")

    with patch("codbeing.models._call_glm") as call_glm:
        section = model_assist_section([TRACE], "# Local report", config, "codex")

    call_glm.assert_not_called()
    assert "external model calls are disabled" in "\n".join(section)


def test_cli_passes_explicit_confirmation_to_external_assist() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="glm-test")

    with (
        patch("codbeing.__main__.external_assist_ready", return_value=True),
        patch("builtins.input", return_value="yes") as ask,
        patch("codbeing.__main__.model_assist_section", return_value=["## Model Assist"])
        as model_assist,
    ):
        _append_model_assist("# Local report", TRACE, config, "glm")

    ask.assert_called_once()
    model_assist.assert_called_once_with(
        [TRACE],
        "# Local report",
        config,
        "glm",
        consent_granted=True,
        assist_requested=True,
    )


def test_glm_assist_does_not_call_provider_without_a_model_selection() -> None:
    config = CodbeingConfig(model_provider="glm", glm_model="   ")

    with (
        patch("codbeing.models._glm_api_key", return_value="configured-secret"),
        patch("codbeing.models._call_glm") as call_glm,
    ):
        section = model_assist_section(
            [TRACE], "# Local report", config, "glm", assist_requested=True
        )

    call_glm.assert_not_called()
    assert "no GLM model is configured" in "\n".join(section)
