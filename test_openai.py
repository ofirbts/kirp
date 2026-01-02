import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def main():
    try:
        # שים לב לשינוי במודל כאן:
        resp = client.embeddings.create(
            model="text-embedding-3-small", 
            input=["hello world"],
        )
        print("Success! Embedding length:", len(resp.data[0].embedding))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()