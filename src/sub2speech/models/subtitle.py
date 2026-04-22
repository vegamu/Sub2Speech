from dataclasses import dataclass
from typing import Optional


@dataclass
class Segment:
    index: int
    start: str
    end: str
    text: str
    speaker: Optional[str] = None
