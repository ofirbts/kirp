from __future__ import annotations

from typing import Dict


PROVIDER_COSTS: Dict[str, Dict[str, float]] = {
    "openai":     {"input": 0.005,  "output": 0.015},
    "groq":       {"input": 0.0002, "output": 0.0006},
    "gemini":     {"input": 0.00015, "output": 0.00035},
    "anthropic":  {"input": 0.003,  "output": 0.015},
    # Local inference — nominal $/1K for quota ceiling (not billing).
    "ollama":     {"input": 0.00001, "output": 0.00003},
}


def estimate_call_ceiling_usd(provider: str, tokens_in: int, max_output_tokens: int) -> float:
    """Upper-bound estimated USD for a single call (pre-invoke quota check)."""
    costs = PROVIDER_COSTS.get(provider, {"input": 0.0, "output": 0.0})
    return (tokens_in * costs["input"] + max_output_tokens * costs["output"]) / 1000.0


def track_cost(provider: str, tokens_in: int, tokens_out: int) -> float:
    """
    Estimate cost in USD for a given provider and token usage.

    Prices are per-1K tokens. This helper is intentionally simple and
    is used for observability and cost awareness rather than billing.
    """
    costs = PROVIDER_COSTS.get(provider, {"input": 0.0, "output": 0.0})
    cost = (tokens_in * costs["input"] + tokens_out * costs["output"]) / 1000.0
    print(f"[COST] {provider}: ${cost:.4f} ({tokens_in}/{tokens_out} tokens)")
    return cost

