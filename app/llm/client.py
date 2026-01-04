from typing import Optional

async def llm_call(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Unified LLM call interface.
    Later: OpenAI / Azure / local model
    """
    # TEMP mock – שלב 6
    return f"[LLM RESPONSE MOCK]\n{prompt}"
