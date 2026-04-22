import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

import edge_tts

CACHE_TTL_SECONDS = 24 * 3600

ALLOWED_LANGUAGE_PREFIXES = {
    "Tiếng Việt": ["vi-"],
    "Tiếng Anh (Tất cả)": ["en-"],
    "Tiếng Nhật": ["ja-"],
    "Tiếng Trung": ["zh-"],
    "Tiếng Hàn": ["ko-"],
    "Tiếng Pháp": ["fr-"],
    "Tiếng Nga": ["ru-"],
}


@dataclass
class VoiceInfo:
    short_name: str
    display_name: str
    gender: str
    locale: str


async def _fetch_voices() -> list[dict]:
    return await edge_tts.list_voices()


def _load_cache(cache_path: Path) -> list[dict] | None:
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - data.get("timestamp", 0) > CACHE_TTL_SECONDS:
        return None
    return data.get("voices", [])


def get_grouped_voices(cache_path: Path) -> dict[str, list[VoiceInfo]]:
    voices = _load_cache(cache_path)
    if voices is None:
        voices = asyncio.run(_fetch_voices())
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"timestamp": int(time.time()), "voices": voices}, ensure_ascii=False),
            encoding="utf-8",
        )

    grouped: dict[str, list[VoiceInfo]] = {k: [] for k in ALLOWED_LANGUAGE_PREFIXES}
    for voice in voices:
        locale = voice.get("Locale", "")
        short_name = voice.get("ShortName", "")
        display_name = voice.get("FriendlyName", short_name)
        gender = voice.get("Gender", "Unknown")
        if not locale or not short_name:
            continue
        for label, prefixes in ALLOWED_LANGUAGE_PREFIXES.items():
            if any(locale.lower().startswith(prefix.lower()) for prefix in prefixes):
                grouped[label].append(
                    VoiceInfo(
                        short_name=short_name,
                        display_name=display_name,
                        gender=gender,
                        locale=locale,
                    )
                )
                break
    for label in list(grouped.keys()):
        grouped[label].sort(key=lambda item: (item.locale, item.display_name))
        if not grouped[label]:
            grouped.pop(label, None)
    return grouped
