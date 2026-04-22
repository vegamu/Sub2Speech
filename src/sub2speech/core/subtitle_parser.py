import re
from pathlib import Path

from sub2speech.models.subtitle import Segment

SRT_BLOCK_PATTERN = re.compile(
    r"(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n{2,}|\Z)",
    re.DOTALL,
)

SPEAKER_PATTERNS = [
    re.compile(r"^\s*\[([^\]]+)\]\s*:?\s*(.*)$", re.DOTALL),
    re.compile(r"^([A-Za-z0-9_\-\u00C0-\u024F\u1E00-\u1EFF ]+):\s*(.*)$", re.DOTALL),
]


def extract_speaker(raw_text: str) -> tuple[str | None, str]:
    text = raw_text.strip()
    for pattern in SPEAKER_PATTERNS:
        match = pattern.match(text)
        if match:
            speaker = match.group(1).strip()
            content = match.group(2).strip()
            if speaker and content:
                return speaker, content
    return None, text


def load_srt(path: str) -> list[Segment]:
    content = Path(path).read_text(encoding="utf-8-sig")
    blocks = SRT_BLOCK_PATTERN.findall(content)
    segments: list[Segment] = []
    for idx_str, start, end, text in blocks:
        speaker, cleaned_text = extract_speaker(text.replace("\n", " ").strip())
        segments.append(
            Segment(
                index=int(idx_str),
                start=start,
                end=end,
                text=cleaned_text,
                speaker=speaker,
            )
        )
    return segments


def load_txt(path: str) -> list[Segment]:
    text = Path(path).read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    speaker, cleaned_text = extract_speaker(text.replace("\n", " ").strip())
    chunks = _split_text_by_max_words(cleaned_text, max_words=500)
    segments: list[Segment] = []
    # Với TXT, timeline chỉ để hiển thị; xuất sẽ ghép tuần tự theo thứ tự chunk.
    for idx, chunk in enumerate(chunks, start=1):
        start_sec = (idx - 1) * 10
        end_sec = idx * 10
        segments.append(
            Segment(
                index=idx,
                start=_seconds_to_time(start_sec),
                end=_seconds_to_time(end_sec),
                text=chunk,
                speaker=speaker,
            )
        )
    return segments


def parse_input_file(path: str) -> list[Segment]:
    suffix = Path(path).suffix.lower()
    if suffix == ".srt":
        return load_srt(path)
    if suffix == ".txt":
        return load_txt(path)
    raise ValueError("Chi ho tro file .srt hoac .txt")


def time_to_seconds(value: str) -> float:
    hh, mm, sec_msec = value.split(":")
    sec, msec = sec_msec.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(sec) + int(msec) / 1000.0


def _split_text_by_max_words(text: str, max_words: int = 500) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i : i + max_words]))
    return chunks


def _seconds_to_time(total_seconds: int) -> str:
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d},000"
