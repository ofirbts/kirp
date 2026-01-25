import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified LLM Gateway.
    Handles connection pooling, retries, and model routing.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        self.url = os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        self.limits = httpx.Limits(max_connections=20, max_keepalive_connections=5)

    async def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """שליחת שאילתה ל-Ollama בצורה אופטימלית"""
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, limits=self.limits) as client:
                response = await client.post(f"{self.url}/api/generate", json=payload)
                response.raise_for_status()
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"❌ LLM Gateway Error: {e}")
            raise

# Instance יחיד לכל הפרויקט
ollama_client = LLMClient()