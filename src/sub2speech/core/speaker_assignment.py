import re


def parse_segment_ranges(raw: str, max_index: int) -> set[int]:
    if not raw.strip():
        return set()

    segments: set[int] = set()
    for token in [item.strip() for item in raw.split(",") if item.strip()]:
        if re.fullmatch(r"\d+", token):
            value = int(token)
            _validate(value, max_index)
            segments.add(value)
            continue
        range_match = re.fullmatch(r"(\d+)-(\d+)", token)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if end < start:
                raise ValueError(f"Range khong hop le: {token}")
            for value in range(start, end + 1):
                _validate(value, max_index)
                segments.add(value)
            continue
        raise ValueError(f"Dinh dang khong hop le: {token}")
    return segments


def check_overlap(assignments: dict[str, set[int]]) -> dict[int, list[str]]:
    owner_map: dict[int, list[str]] = {}
    for speaker, segments in assignments.items():
        for seg in segments:
            owner_map.setdefault(seg, []).append(speaker)
    return {seg: owners for seg, owners in owner_map.items() if len(owners) > 1}


def _validate(value: int, max_index: int) -> None:
    if value < 1 or value > max_index:
        raise ValueError(f"So thu tu doan {value} ngoai pham vi 1..{max_index}")
