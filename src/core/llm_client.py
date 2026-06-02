"""
Unified LLM Client — OpenAI / Anthropic / Ollama (pluggable).

All agents use this client for intelligence.
"""

from __future__ import annotations

import logging
import math
import os
import re
from typing import Any, Tuple

from src.core.cost_tracker import track_cost

logger = logging.getLogger(__name__)


async def _record_llm_timeline_step(routing_tag: str, ok: bool, error: str | None) -> None:
    """Append RunController step llm_call_<tag> when llm_run_context has a run_id."""
    from src.core.llm_run_context import get_llm_run_id

    rid = get_llm_run_id()
    if not rid:
        return
    safe = re.sub(r"[^a-z0-9_]+", "_", (routing_tag or "unknown").lower()).strip("_") or "unknown"
    step = f"llm_call_{safe}"
    try:
        from src.core.run_controller import get_run_controller

        rc = get_run_controller()
        await rc.update_step(rid, step, "completed" if ok else "failed", error=error)
    except Exception as e:
        logger.warning("llm_timeline_record_failed run_id=%s step=%s err=%s", rid, step, e)


class LLMClient:
    """Unified LLM client. Provider-agnostic."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        *,
        routing_tag: str | None = None,
    ) -> None:
        """
        Initialize an LLM client.

        - provider: explicit provider override (openai, anthropic, groq, gemini, ollama).
          If None, uses LLM_PROVIDER env var (default: openai).
        - model: optional model preference; if None, uses provider-specific env default.
        - routing_tag: logical route id for run timeline (e.g. gemma4); defaults to provider.
        """
        env_provider = (os.getenv("LLM_PROVIDER", "openai") or "openai").lower()
        self._provider = (provider or env_provider).lower()
        self._model = model  # may be None → fall back to env defaults per provider
        self._routing_tag = routing_tag or self._provider
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize provider-specific client."""
        if self._provider == "openai":
            try:
                from openai import AsyncOpenAI
                api_key = os.getenv("OPENAI_API_KEY", "")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not set")
                    return
                self._client = AsyncOpenAI(api_key=api_key)
                logger.info("LLMClient initialized: OpenAI")
            except ImportError:
                logger.warning("openai not installed")
        elif self._provider == "anthropic":
            try:
                from anthropic import AsyncAnthropic
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
                if not api_key:
                    logger.warning("ANTHROPIC_API_KEY not set")
                    return
                self._client = AsyncAnthropic(api_key=api_key)
                logger.info("LLMClient initialized: Anthropic")
            except ImportError:
                logger.warning("anthropic not installed")
        elif self._provider == "groq":
            try:
                from langchain_groq import ChatGroq
                api_key = os.getenv("GROQ_API_KEY", "")
                if not api_key:
                    logger.warning("GROQ_API_KEY not set")
                    return
                self._client = ChatGroq(
                    model=self._model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    api_key=api_key,
                )
                logger.info("LLMClient initialized: Groq")
            except ImportError:
                logger.warning("langchain-groq not installed")
        elif self._provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
                if not api_key:
                    logger.warning("GEMINI_API_KEY not set")
                    return
                self._client = ChatGoogleGenerativeAI(
                    model=self._model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                    google_api_key=api_key,
                )
                logger.info("LLMClient initialized: Gemini")
            except ImportError:
                logger.warning("langchain-google-genai not installed")
        elif self._provider == "ollama":
            self._ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
            self._ollama_model = self._model or os.getenv("OLLAMA_MODEL", "llama3")
            logger.info("LLMClient initialized: Ollama (%s)", self._ollama_model)
        else:
            logger.warning("Unknown LLM provider: %s", self._provider)

    async def _resolve_quota_tenant_id(self) -> str | None:
        """Tenant for LLM quota: explicit context, else RunController state for current run_id."""
        from src.core.llm_run_context import get_llm_run_id, get_llm_tenant_id

        tid = get_llm_tenant_id()
        if tid:
            return tid
        rid = get_llm_run_id()
        if not rid:
            return None
        try:
            from src.core.run_controller import get_run_controller

            st = await get_run_controller().get_run_state(
                rid, tenant_id=get_llm_tenant_id()
            )
            if st and st.tenant_id:
                return str(st.tenant_id)
        except Exception as e:
            logger.debug("llm quota tenant resolve failed: %s", e)
        return None

    async def invoke(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Invoke LLM. Returns text response and tracks estimated cost."""
        from src.core.cost_tracker import estimate_call_ceiling_usd
        from src.core.quotas import (
            check_tenant_llm_budget,
            get_effective_llm_quota_limit_usd,
            increment_tenant_llm_cost,
        )

        def _approx_tokens(text: str) -> int:
            return max(1, math.ceil(len(text) / 4))

        tokens_in = _approx_tokens((system_prompt or "") + "\n" + prompt)
        tenant_id = await self._resolve_quota_tenant_id()
        limit = get_effective_llm_quota_limit_usd()
        if tenant_id and limit > 0:
            est = estimate_call_ceiling_usd(self._provider, tokens_in, max_tokens)
            await check_tenant_llm_budget(tenant_id, est)

        text, spent = await self._invoke_untracked(
            prompt, system_prompt, temperature=temperature, max_tokens=max_tokens
        )
        ok = not (
            text.startswith("LLM Error:")
            or text.startswith("LLM not configured")
        )
        await _record_llm_timeline_step(self._routing_tag, ok, None if ok else text[:500])
        if tenant_id and limit > 0 and ok and spent > 0:
            await increment_tenant_llm_cost(tenant_id, spent)
        return text

    async def _invoke_untracked(
        self,
        prompt: str,
        system_prompt: str | None = None,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Tuple[str, float]:
        """LLM call without quota / timeline side-effects (internal). Returns (text, cost_usd)."""
        provider = self._provider

        def _approx_tokens(text: str) -> int:
            # Very rough heuristic: ~4 chars per token.
            return max(1, math.ceil(len(text) / 4))

        tokens_in = _approx_tokens((system_prompt or "") + "\n" + prompt)
        tokens_out = 0

        if provider == "openai" and self._client:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                r = await self._client.chat.completions.create(
                    model=self._model or os.getenv("OPENAI_MODEL", "gpt-4"),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Use official usage if available
                try:
                    usage = getattr(r, "usage", None)
                    if usage is not None:
                        tokens_in = int(getattr(usage, "prompt_tokens", tokens_in) or tokens_in)
                        tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                except Exception:
                    pass
                cost = track_cost(provider, tokens_in, tokens_out)
                return (r.choices[0].message.content or "", cost)
            except Exception as e:
                logger.error("OpenAI invoke failed: %s", e)
                return (f"LLM Error: {e}", 0.0)
        elif provider == "anthropic" and self._client:
            try:
                system = system_prompt or ""
                r = await self._client.messages.create(
                    model=self._model or os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                # Anthropic usage (best-effort; shape may vary)
                try:
                    usage = getattr(r, "usage", None)
                    if usage is not None:
                        tokens_in = int(getattr(usage, "input_tokens", tokens_in) or tokens_in)
                        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
                except Exception:
                    pass
                cost = track_cost(provider, tokens_in, tokens_out)
                return (r.content[0].text if r.content else "", cost)
            except Exception as e:
                logger.error("Anthropic invoke failed: %s", e)
                return (f"LLM Error: {e}", 0.0)
        elif provider == "groq" and self._client:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                msgs = []
                if system_prompt:
                    msgs.append(SystemMessage(content=system_prompt))
                msgs.append(HumanMessage(content=prompt))
                r = await self._client.ainvoke(msgs)
                text = (r.content if hasattr(r, "content") else str(r)) or ""
                tokens_out = _approx_tokens(text)
                cost = track_cost(provider, tokens_in, tokens_out)
                return (text, cost)
            except Exception as e:
                logger.error("Groq invoke failed: %s", e)
                return (f"LLM Error: {e}", 0.0)
        elif provider == "gemini" and self._client:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                msgs = []
                if system_prompt:
                    msgs.append(SystemMessage(content=system_prompt))
                msgs.append(HumanMessage(content=prompt))
                r = await self._client.ainvoke(msgs)
                text = (r.content if hasattr(r, "content") else str(r)) or ""
                tokens_out = _approx_tokens(text)
                cost = track_cost(provider, tokens_in, tokens_out)
                return (text, cost)
            except Exception as e:
                logger.error("Gemini invoke failed: %s", e)
                return (f"LLM Error: {e}", 0.0)
        elif provider == "ollama":
            try:
                import httpx
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(
                        f"{self._ollama_url}/api/generate",
                        json={
                            "model": self._ollama_model,
                            "prompt": full_prompt,
                            "stream": False,
                            "options": {"temperature": temperature},
                        },
                    )
                    r.raise_for_status()
                    text = r.json().get("response", "").strip()
                    tokens_out = _approx_tokens(text)
                    cost = track_cost(provider, tokens_in, tokens_out)
                    return (text, cost)
            except Exception as e:
                logger.error("Ollama invoke failed: %s", e)
                return (f"LLM Error: {e}", 0.0)
        else:
            # Provider not initialized (missing API key or unknown provider)
            hints = {
                "openai": "Set OPENAI_API_KEY",
                "anthropic": "Set ANTHROPIC_API_KEY",
                "groq": "Set GROQ_API_KEY",
                "gemini": "Set GEMINI_API_KEY or GOOGLE_API_KEY",
                "ollama": "Set OLLAMA_URL (default http://ollama:11434) and run Ollama locally",
            }
            hint = hints.get(provider, f"Set API key for provider '{provider}'")
            return (f"LLM not configured ({provider}). {hint}.", 0.0)

    async def ainvoke(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> Any:
        """LangChain-compatible interface."""
        text = await self.invoke(prompt, system_prompt, **kwargs)
        # Return LangChain-style message
        class Message:
            def __init__(self, content: str):
                self.content = content
        return Message(text)


# Global singleton
_llm_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """Get global LLM client (legacy). Prefer src.core.llm_router.get_llm_for_task."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
