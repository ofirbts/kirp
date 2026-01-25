from enum import Enum


class KnowledgePlane(str, Enum):
    KNOWLEDGE = "knowledge"
    SESSION = "session"
    EVENT = "event"
