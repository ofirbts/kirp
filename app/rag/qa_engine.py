from typing import List
from langchain_openai import ChatOpenAI
from app.rag.vector_store import get_vector_store
from app.llm.client import llm_call

async def retrieve_relevant_chunks(question: str, k: int = 3) -> List[str]:
    """LangChain retriever only (no similarity_search dependency)"""
    try:
        store = get_vector_store()
        if not store:
            return []
        retriever = store.as_retriever(search_kwargs={"k": k})
        docs = retriever.invoke(question)
        return [doc.page_content for doc in docs]
    except Exception:
        return []

async def answer_with_rag(question: str) -> str:
    """Full RAG pipeline"""
    chunks = await retrieve_relevant_chunks(question)
    
    if not chunks:
        return "No relevant information found. Try adding data via /ingest."
    
    context = "\n\n".join(chunks[:4])
    
    prompt = f"""
You are a helpful assistant. Answer in Hebrew only, concise and precise.
Use ONLY the following context. If answer not found, say "אין לי מידע על זה".

Context:
{context}

Question: {question}

Answer:"""

    return await llm_call(prompt)
