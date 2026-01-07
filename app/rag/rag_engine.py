from typing import List
from app.rag.retriever import retrieve_context

def generate_answer(context: List[str], question: str) -> str:
    """Generate answer using RAG + Memory Ranking - SYNCHRONOUS"""
    context_text = "\n\n---\n\n".join(context)
    return f"""📊 Ranked Memories (Recency + Similarity):

{context_text}

Q: {question}"""
