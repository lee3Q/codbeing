"""Local user configuration for codbeing."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path("private/codbeing-config.json")
DEFAULT_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_GLM_MODEL = "glm-4.5"
PROVIDERS = ("codex", "glm")


@dataclass(frozen=True)
class CodbeingConfig:
    model_provider: str = "codex"
    glm_model: str = DEFAULT_GLM_MODEL
    glm_base_url: str = DEFAULT_GLM_BASE_URL


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> CodbeingConfig:
    if not path.exists():
        return CodbeingConfig()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return CodbeingConfig()
    provider = str(payload.get("model_provider", "codex")).lower()
    if provider not in PROVIDERS:
        provider = "codex"
    return CodbeingConfig(
        model_provider=provider,
        glm_model=str(payload.get("glm_model", DEFAULT_GLM_MODEL)),
        glm_base_url=str(payload.get("glm_base_url", DEFAULT_GLM_BASE_URL)),
    )


def save_config(config: CodbeingConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "model_provider": config.model_provider,
                "glm_model": config.glm_model,
                "glm_base_url": config.glm_base_url,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def resolve_provider(config: CodbeingConfig, override: str | None = None) -> str:
    if override and override != "auto":
        provider = override.lower()
        return provider if provider in PROVIDERS else config.model_provider
    return config.model_provider


def glm_api_key_present() -> bool:
    return _glm_api_key() is not None


def glm_runtime_env() -> dict[str, str]:
    """Return GLM-related runtime env without printing or persisting secrets."""
    values: dict[str, str] = {}
    token = _glm_api_key()
    if token:
        values["ANTHROPIC_AUTH_TOKEN"] = token

    for name in (
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_MODEL",
        "API_TIMEOUT_MS",
    ):
        value = (
            os.environ.get(name)
            or _dotenv_value(Path(".env"), (name,))
            or _dotenv_value(Path("private/.env"), (name,))
            or _zshrc_assignment(name)
        )
        if value:
            values[name] = value
    return values


def _glm_api_key() -> str | None:
    for name in (
        "CODBEING_GLM_API_KEY",
        "GLM_API_KEY",
        "ZHIPUAI_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
    ):
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    for path in (Path(".env"), Path("private/.env")):
        value = _dotenv_value(
            path,
            (
                "CODBEING_GLM_API_KEY",
                "GLM_API_KEY",
                "ZHIPUAI_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
            ),
        )
        if value and value.strip():
            return value.strip()
    shell_value = _zshrc_assignment("ANTHROPIC_AUTH_TOKEN")
    return shell_value.strip() if shell_value and shell_value.strip() else None


def _zshrc_assignment(name: str) -> str | None:
    if os.environ.get("CODBEING_DISABLE_SHELL_KEY_LOOKUP") == "1":
        return None
    path = Path.home() / ".zshrc"
    if not path.exists():
        return None
    pattern = re.compile(rf"\b{re.escape(name)}=(?P<value>\"[^\"]*\"|'[^']*'|[^\s\\]+)")
    match = pattern.search(path.read_text(encoding="utf-8"))
    if match is None:
        return None
    return match.group("value").strip().strip("'\"") or None
    return None


def _dotenv_value(path: Path, names: tuple[str, ...]) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() in names:
            return value.strip().strip("'\"") or None
    return None


def config_summary(config: CodbeingConfig) -> dict[str, Any]:
    runtime_env = glm_runtime_env()
    return {
        "model_provider": config.model_provider,
        "glm_model": runtime_env.get("ANTHROPIC_DEFAULT_SONNET_MODEL", config.glm_model),
        "glm_base_url": runtime_env.get("ANTHROPIC_BASE_URL", config.glm_base_url),
        "glm_api_key_present": glm_api_key_present(),
        "glm_anthropic_compatible_env_present": bool(
            runtime_env.get("ANTHROPIC_BASE_URL")
            and runtime_env.get("ANTHROPIC_AUTH_TOKEN")
        ),
    }
