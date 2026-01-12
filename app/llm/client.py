import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def get_llm():
    """
    Returns an instance of ChatOpenAI using the API key from the environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("⚠️ OPENAI_API_KEY not found in environment. Falling back to dummy.")
        class DummyLLM:
            async def apredict(self, prompt: str):
                return "Error: No API Key provided."
        return DummyLLM()

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=api_key
    )

async def llm_call(prompt: str) -> str:
    """Helper function for simple calls"""
    llm = get_llm()
    return await llm.apredict(prompt)
