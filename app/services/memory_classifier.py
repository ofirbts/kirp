from app.models.memory import MemoryType


def classify_memory(text: str) -> MemoryType:
    t = text.lower()

    if "i love" in t or "i like" in t or "אני אוהב" in t:
        return MemoryType.PREFERENCE

    if "tomorrow" in t or "meeting" in t or "פגישה" in t:
        return MemoryType.EVENT

    if "is" in t or "אני" in t:
        return MemoryType.FACT

    return MemoryType.NOTE
