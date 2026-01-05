from app.rag.qa_engine import answer_with_rag

async def intelligent_query(question: str) -> str:
    """
    High-level intelligent query interface.
    """
    return await answer_with_rag(question)
