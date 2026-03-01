from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedSection:
    """A section extracted from a document."""
    title: str
    text: str
    level: int              # Heading depth (1=H1, 2=H2, etc.)
    page_number: Optional[int] = None
    images: list[dict] = field(default_factory=list)
    # Each dict: {"data": base64_str, "media_type": str, "caption": str}


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> list[ParsedSection]:
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        ...
