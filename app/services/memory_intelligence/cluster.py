from app.models.memory import MemoryRecord


def cluster_memories(memories: list[MemoryRecord]) -> dict:
    """
    Groups related memories into topics or threads.
    """
    clusters = {}

    for mem in memories:
        key = mem.tags[0] if mem.tags else "general"
        clusters.setdefault(key, []).append(mem)

    return clusters
