from dataclasses import dataclass, field


@dataclass
class Speaker:
    name: str
    voice: str = ""
    language_group: str = ""
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
    segments: set[int] = field(default_factory=set)
