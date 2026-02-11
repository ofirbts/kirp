from __future__ import annotations

import os
from typing import Literal

from src.core.llm_client import LLMClient


TaskType = Literal["critical", "reasoning", "bulk", "ui", "dev"]


# Default provider/model per task. Override via env: REASONING_PROVIDER, BULK_PROVIDER, etc.
PROVIDERS: dict[str, dict[str, str]] = {
    "critical":  {"provider": "openai",    "model": "gpt-4o-mini"},
    "reasoning": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
    "bulk":      {"provider": "groq",      "model": "llama-3.1-8b-instant"},
    "ui":        {"provider": "gemini",    "model": "gemini-1.5-flash"},
    "dev":       {"provider": "ollama",    "model": "llama3"},
}

# Env keys that override provider per task: REASONING_PROVIDER, BULK_PROVIDER, ...
_ENV_PROVIDER_KEYS: dict[str, str] = {
    "critical":  "CRITICAL_PROVIDER",
    "reasoning": "REASONING_PROVIDER",
    "bulk":      "BULK_PROVIDER",
    "ui":        "UI_PROVIDER",
    "dev":       "DEV_PROVIDER",
}

# When overriding provider via env, which model to use (provider -> default model)
_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "openai":    "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "groq":      "llama-3.1-8b-instant",
    "gemini":    "gemini-1.5-flash",
    "ollama":    "llama3",
}


def get_llm_for_task(task_type: TaskType = "bulk") -> LLMClient:
    """
    Return an LLMClient instance configured for the given task type.

    - Defaults from PROVIDERS; override with REASONING_PROVIDER, BULK_PROVIDER, etc.
    - E.g. REASONING_PROVIDER=groq makes /ask use Groq instead of Anthropic.
    """
    cfg = PROVIDERS.get(task_type, PROVIDERS["bulk"]).copy()
    env_key = _ENV_PROVIDER_KEYS.get(task_type)
    if env_key:
        env_provider = (os.getenv(env_key) or "").strip().lower()
        if env_provider:
            cfg["provider"] = env_provider
            cfg["model"] = _PROVIDER_DEFAULT_MODEL.get(env_provider, cfg.get("model", ""))
    return LLMClient(provider=cfg["provider"], model=cfg["model"])


def route_task(task_category: TaskType) -> LLMClient:
    """Alias for get_llm_for_task to match the spec."""
    return get_llm_for_task(task_category)

