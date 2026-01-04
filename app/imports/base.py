from abc import ABC, abstractmethod
from typing import Iterable


from dataclasses import dataclass

@dataclass
class ImportChunk:
    content: str
    source: str



class BaseImporter(ABC):

    @abstractmethod
    def parse(self, raw_data: str) -> Iterable[ImportChunk]:
        """
        Parse raw input into meaningful chunks.
        """
        pass
