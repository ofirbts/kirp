from app.rag.retriever import retrieve_context
from app.rag.rag_engine import generate_answer

async def answer_with_rag(question: str, k: int = 5) -> str:
    memories = retrieve_context(question, k=k)
    return generate_answer(memories, question)
