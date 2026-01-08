from typing import List, Union, Dict, Any


def format_context_for_answer(context: List[Union[str, Dict[str, Any]]]) -> str:
    parts: List[str] = []
    for idx, item in enumerate(context, start=1):
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            expl = item.get("explanation") or {}

            score = expl.get("confidence") or item.get("score")
            concepts = expl.get("matched_concepts") or []
            overlap = expl.get("query_overlap") or []
            source = expl.get("source")

            header = (
                f"[{idx}] score={score:.3f}"
                if isinstance(score, (int, float))
                else f"[{idx}]"
            )
            if source:
                header += f" | source={source}"

            meta_line = ""
            if concepts or overlap:
                meta_bits = []
                if overlap:
                    meta_bits.append(f"overlap={overlap}")
                if concepts:
                    meta_bits.append(f"concepts={concepts}")
                meta_line = " (" + ", ".join(meta_bits) + ")"

            parts.append(f"{header}{meta_line}\n{text}")
        else:
            parts.append(str(item))

    return "\n\n---\n\n".join(parts)


def generate_answer(
    context: List[Union[str, Dict[str, Any]]],
    question: str,
) -> str:
    context_text = format_context_for_answer(context)
    return f"""📊 Ranked Memories (Similarity + Recency + Concepts):

{context_text}

Q: {question}"""
