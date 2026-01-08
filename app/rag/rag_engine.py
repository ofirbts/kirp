from typing import List, Union, Dict, Any


def format_context_for_answer(context: List[Union[str, Dict[str, Any]]]) -> str:
    """
    מייצר טקסט נח לקריאה מתוך רשימת זיכרונות.
    """
    parts: List[str] = []
    for idx, item in enumerate(context, start=1):
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            score = item.get("score")
            explanation = item.get("explanation") or {}
            concepts = explanation.get("matched_concepts") or []
            overlap = explanation.get("query_overlap") or []
            confidence = explanation.get("confidence")
            source = explanation.get("source")

            header = f"[{idx}] score={score:.3f}" if isinstance(score, (int, float)) else f"[{idx}]"
            if confidence is not None:
                header += f" | confidence={confidence:.3f}"
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
    question: str
) -> str:
    """
    מייצר תשובה טקסטואלית, אבל מיועד גם לכך שה־API יחזיר את ה־sources כ־JSON.
    """
    context_text = format_context_for_answer(context)

    return f"""📊 Ranked Memories (Similarity + Recency + Concepts):

{context_text}

Q: {question}"""
