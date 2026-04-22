import asyncio
import time

import edge_tts

from sub2speech.utils.logging_utils import log_error, log_info


async def synthesize(
    text: str,
    voice: str,
    out_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    await communicate.save(out_path)


def synthesize_sync(
    text: str,
    voice: str,
    out_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    retries: int = 5,
) -> None:
    error: Exception | None = None
    for attempt in range(retries):
        try:
            log_info(
                f"EdgeTTS synth attempt={attempt + 1}/{retries} voice={voice} rate={rate} volume={volume} pitch={pitch}"
            )
            asyncio.run(
                synthesize(
                    text=text,
                    voice=voice,
                    out_path=out_path,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                )
            )
            return
        except Exception as exc:  # pragma: no cover
            error = exc
            log_error(f"EdgeTTS synth failed attempt={attempt + 1}/{retries}: {exc}")
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Khong the synthesize voice sau {retries} lan: {error}") from error
