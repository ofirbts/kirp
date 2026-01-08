# app/llm/client.py

async def llm_call(prompt: str) -> str:
    return "NONE"  # סטאב זמני

def get_llm():
    class DummyLLM:
        async def apredict(self, prompt: str):
            return "note"
    return DummyLLM()
