import os
from langchain_openai import OpenAIEmbeddings

def get_embeddings():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("חסר OPENAI_API_KEY! הגדר export OPENAI_API_KEY=sk-...")
    return OpenAIEmbeddings(openai_api_key=api_key)
