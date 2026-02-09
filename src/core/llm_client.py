"""
Unified LLM Client — OpenAI / Anthropic / Ollama (pluggable).

All agents use this client for intelligence.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client. Provider-agnostic."""

    def __init__(self) -> None:
        self._provider = (os.getenv("LLM_PROVIDER", "openai") or "openai").lower()
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
                    model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
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
                    model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                    google_api_key=api_key,
                )
                logger.info("LLMClient initialized: Gemini")
            except ImportError:
                logger.warning("langchain-google-genai not installed")
        elif self._provider == "ollama":
            self._ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
            self._ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
            logger.info("LLMClient initialized: Ollama (%s)", self._ollama_model)
        else:
            logger.warning("Unknown LLM provider: %s", self._provider)

    async def invoke(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Invoke LLM. Returns text response."""
        if self._provider == "openai" and self._client:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                r = await self._client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4"),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return r.choices[0].message.content or ""
            except Exception as e:
                logger.error("OpenAI invoke failed: %s", e)
                return f"LLM Error: {e}"
        elif self._provider == "anthropic" and self._client:
            try:
                system = system_prompt or ""
                r = await self._client.messages.create(
                    model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                return r.content[0].text if r.content else ""
            except Exception as e:
                logger.error("Anthropic invoke failed: %s", e)
                return f"LLM Error: {e}"
        elif self._provider == "groq" and self._client:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                msgs = []
                if system_prompt:
                    msgs.append(SystemMessage(content=system_prompt))
                msgs.append(HumanMessage(content=prompt))
                r = await self._client.ainvoke(msgs)
                return (r.content if hasattr(r, "content") else str(r)) or ""
            except Exception as e:
                logger.error("Groq invoke failed: %s", e)
                return f"LLM Error: {e}"
        elif self._provider == "gemini" and self._client:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                msgs = []
                if system_prompt:
                    msgs.append(SystemMessage(content=system_prompt))
                msgs.append(HumanMessage(content=prompt))
                r = await self._client.ainvoke(msgs)
                return (r.content if hasattr(r, "content") else str(r)) or ""
            except Exception as e:
                logger.error("Gemini invoke failed: %s", e)
                return f"LLM Error: {e}"
        elif self._provider == "ollama":
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
                    return r.json().get("response", "").strip()
            except Exception as e:
                logger.error("Ollama invoke failed: %s", e)
                return f"LLM Error: {e}"
        else:
            return "LLM not configured"

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
    """Get global LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
