# app/llm/client.py

async def llm_call(prompt: str) -> str:
    return "NONE"  # סטאב זמני

def get_llm():
    class DummyLLM:
        async def apredict(self, prompt: str):
            return "note"
    return DummyLLM()

#from langchain_openai import ChatOpenAI
#import os

#def get_llm():
 #   return ChatOpenAI(
  #      model="gpt-4o-mini",
  #      temperature=0,
   #     openai_api_key=os.getenv("OPENAI_API_KEY")
    #)
