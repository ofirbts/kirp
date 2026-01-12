from app.services.memory_classifier import classify_memory
from app.rag.chunker import chunk_text
from app.rag.vector_store import add_texts_with_metadata
from typing import Dict, Any, List

def classify_memory(text: str) -> str:  # ← string, לא async!
    """Simple sync classifier"""
    t = text.lower()
    if "tomorrow" in t or "buy" in t:
        return "task"
    if "meeting" in t or "call" in t:
        return "event" 
    return "knowledge"

def ingest_text(text: str, source: str = "api", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """🔥 Working pipeline - NO async dependencies"""
    if metadata is None:
        metadata = {}
    
    # 1. Classify
    memory_type = classify_memory(text)
    
    # 2. Chunk + metadata
    chunks = chunk_text(text)
    metadata_list = [{"memory_type": memory_type, "source": source} for _ in chunks]
    
    # 3. Vector store
    chunks_added = add_texts_with_metadata(chunks, metadata_list)
    
    
    return {
        "memory_type": memory_type,
        "chunks_added": chunks_added
    }
