import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# חיפוש הקובץ בנתיב המוחלט כדי למנוע טעויות
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path=env_path)

def get_api_key():
    # ניסיון 1: מה-env הנטען
    api_key = os.getenv("OPENAI_API_KEY")
    
    # ניסיון 2: ישירות מהסביבה של המערכת
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        raise ValueError(f"Missing OPENAI_API_KEY! Searched in: {env_path}")
    return api_key

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small", 
    openai_api_key=get_api_key()
)