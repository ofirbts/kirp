from fastapi import APIRouter
from pydantic import BaseModel
from app.rag.qa_engine import ask_question

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

@router.post("/")
def query_knowledge(data: QueryRequest):
    answer = ask_question(data.question)
    return {"answer": answer}
