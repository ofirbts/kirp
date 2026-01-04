from abc import ABC, abstractmethod
from typing import Iterable


class ImportChunk:
    def __init__(self, content: str, source: str):
        self.content = content
        self.source = source


class BaseImporter(ABC):

    @abstractmethod
    def parse(self, raw_data: str) -> Iterable[ImportChunk]:
        """
        Parse raw input into meaningful chunks.
        """
        pass
