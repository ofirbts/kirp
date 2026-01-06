from openai import OpenAI
from typing import List

client = OpenAI()


SYSTEM_PROMPT = """You are KIRP, a personal intelligence system.
Answer using ONLY the provided context.
If the answer is not in the context, say: "I don't have enough information yet."
Be concise, factual, and helpful.
"""


def build_prompt(context: List[str], question: str) -> str:
    joined_context = "\n\n---\n\n".join(context)

    return f"""
CONTEXT:
{joined_context}

QUESTION:
{question}

ANSWER:
"""


def generate_answer(context: List[str], question: str) -> str:
    prompt = build_prompt(context, question)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content.strip()
