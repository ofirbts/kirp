from __future__ import annotations

import os
from typing import Literal

from src.core.llm_client import LLMClient


TaskType = Literal["critical", "reasoning", "bulk", "ui", "dev"]

# Logical routes: cost (relative $), latency tier, capabilities (for select_model heuristics).
ROUTING_PROFILES: dict[str, dict[str, object]] = {
    "gemma4": {"cost": 0.1, "latency": "low", "local": True, "reasoning": False},
    "claude": {"cost": 1.5, "latency": "medium", "local": False, "reasoning": True},
    "groq": {"cost": 0.5, "latency": "fastest", "local": False, "reasoning": False},
    "openai_mini": {"cost": 0.2, "latency": "low", "local": False, "reasoning": False},
    "gemini_flash": {"cost": 0.15, "latency": "low", "local": False, "reasoning": False},
    "ollama_dev": {"cost": 0.0, "latency": "medium", "local": True, "reasoning": False},
}

# Default provider/model per task when legacy env overrides are absent.
_PROVIDERS: dict[str, dict[str, str]] = {
    "critical": {"provider": "openai", "model": "gpt-4o-mini", "route": "openai_mini"},
    "reasoning": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "route": "claude"},
    "bulk": {"provider": "ollama", "model": "", "route": "gemma4"},
    "ui": {"provider": "gemini", "model": "gemini-1.5-flash", "route": "gemini_flash"},
    "dev": {"provider": "ollama", "model": "llama3", "route": "ollama_dev"},
}

_ENV_PROVIDER_KEYS: dict[str, str] = {
    "critical": "CRITICAL_PROVIDER",
    "reasoning": "REASONING_PROVIDER",
    "bulk": "BULK_PROVIDER",
    "ui": "UI_PROVIDER",
    "dev": "DEV_PROVIDER",
}

_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-1.5-flash",
    "ollama": "llama3",
}


def _parse_cost_budget(raw: str | None) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def select_model(
    task_type: TaskType,
    latency_budget: str | None = None,
    cost_budget: float | None = None,
) -> str:
    """
    Cost/latency-aware route id (not the raw provider string).
    Gemma4 first for bulk/low-risk; Claude when reasoning and budget allows.
    """
    lat = (latency_budget or os.getenv("LLM_LATENCY_BUDGET") or "medium").strip().lower()
    cost_max = cost_budget if cost_budget is not None else _parse_cost_budget(os.getenv("LLM_COST_BUDGET"))
    if task_type == "reasoning":
        claude_cost = float(ROUTING_PROFILES["claude"]["cost"])  # type: ignore[arg-type]
        groq_cost = float(ROUTING_PROFILES["groq"]["cost"])  # type: ignore[arg-type]
        if cost_max is None or cost_max >= claude_cost:
            return "claude"
        if cost_max >= groq_cost:
            return "groq"
        return "gemma4"

    if task_type == "bulk":
        if lat == "fastest":
            return "groq"
        return "gemma4"

    if task_type == "critical":
        return "openai_mini"

    if task_type == "ui":
        return "gemini_flash"

    return "ollama_dev"


def best_provider(task_type: TaskType, latency_budget: str | None, cost_budget: float | None) -> str:
    """Alias matching the routing spec."""
    return select_model(task_type, latency_budget, cost_budget)


def _llm_client_for_route(route: str) -> LLMClient:
    """Map a route id to LLMClient + routing_tag for run timeline."""
    if route == "gemma4":
        model = (os.getenv("GEMMA4_OLLAMA_MODEL") or os.getenv("GEMMA4_MODEL") or "gemma2").strip()
        return LLMClient(provider="ollama", model=model, routing_tag="gemma4")
    if route == "claude":
        return LLMClient(
            provider="anthropic",
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            routing_tag="claude",
        )
    if route == "groq":
        return LLMClient(
            provider="groq",
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            routing_tag="groq",
        )
    if route == "openai_mini":
        return LLMClient(
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            routing_tag="openai_mini",
        )
    if route == "gemini_flash":
        return LLMClient(
            provider="gemini",
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            routing_tag="gemini_flash",
        )
    return LLMClient(
        provider="ollama",
        model=os.getenv("OLLAMA_MODEL", "llama3"),
        routing_tag="ollama_dev",
    )


def get_llm_for_task(task_type: TaskType = "bulk") -> LLMClient:
    """
    Return an LLMClient for the task type.

    - Dynamic route via select_model unless a legacy *_{PROVIDER} env overrides the provider.
    - Bulk defaults to Gemma4 (local Ollama) when Ollama is configured.
    """
    env_key = _ENV_PROVIDER_KEYS.get(task_type)
    if env_key:
        env_provider = (os.getenv(env_key) or "").strip().lower()
        if env_provider:
            cfg = _PROVIDERS.get(task_type, _PROVIDERS["bulk"]).copy()
            cfg["provider"] = env_provider
            cfg["model"] = _PROVIDER_DEFAULT_MODEL.get(env_provider, cfg.get("model", ""))
            return LLMClient(
                provider=cfg["provider"],
                model=cfg["model"] or None,
                routing_tag=env_provider,
            )

    route = select_model(
        task_type,
        os.getenv("LLM_LATENCY_BUDGET"),
        _parse_cost_budget(os.getenv("LLM_COST_BUDGET")),
    )
    return _llm_client_for_route(route)


def route_task(task_category: TaskType) -> LLMClient:
    """Alias for get_llm_for_task to match the spec."""
    return get_llm_for_task(task_category)
