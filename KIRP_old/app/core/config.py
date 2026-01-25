import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    MONGO_URI = st.secrets.get("MONGO_URI") or os.getenv("MONGO_URI")
    MONGO_DB_NAME = st.secrets.get("MONGO_DB_NAME") or os.getenv("MONGO_DB_NAME", "kirp")
    
    NOTION_TOKEN = st.secrets.get("NOTION_TOKEN") or os.getenv("NOTION_TOKEN")
    NOTION_TASKS_DB_ID = st.secrets.get("NOTION_TASKS_DB_ID") or os.getenv("NOTION_TASKS_DB_ID")

    # שאר ההגדרות
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))