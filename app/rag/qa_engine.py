from langchain_openai import ChatOpenAI
from app.rag.vector_store import get_vector_store


def ask_question(question: str) -> str:
    store = get_vector_store()
    retriever = store.as_retriever(search_kwargs={"k": 3})

    # LangChain 1.x API
    docs = retriever.invoke(question)

    if not docs:
        return "No relevant information found."

    context = "\n\n".join(doc.page_content for doc in docs)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    prompt = f"""
You are a helpful assistant.
Answer the question using ONLY the context below.

Context:
{context}

Question:
{question}
"""

    response = llm.invoke(prompt)
    return response.content
