from __future__ import annotations

import asyncio
import random
import re
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

import edge_tts
from edge_tts.exceptions import (
    EdgeTTSException,
    NoAudioReceived,
    SkewAdjustmentError,
    UnexpectedResponse,
    UnknownResponse,
    WebSocketError,
)

from sub2speech.utils.logging_utils import log_error, log_info

DEFAULT_RETRIES = 5
_BASE_DELAY = 0.8
_DELAY_CAP = 10.0
_RETRYABLE_EXC: tuple[type[BaseException], ...] = (
    NoAudioReceived,
    WebSocketError,
    UnknownResponse,
    UnexpectedResponse,
    SkewAdjustmentError,
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)


@dataclass
class TtsJob:
    seg_index: int
    text: str
    voice: str
    out_path: str
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"


def _retry_after_from_exc(exc: BaseException) -> float | None:
    # edge-tts hiện không expose Retry-After cấu trúc, parse từ message nếu có.
    message = str(exc)
    match = re.search(r"retry[\-\s]?after[^\d]*(\d+(?:\.\d+)?)", message, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _is_rate_limited(exc: BaseException) -> bool:
    message = str(exc)
    return "429" in message or "Too Many Requests" in message


def _compute_backoff(attempt: int) -> float:
    delay = min(_DELAY_CAP, _BASE_DELAY * (2 ** attempt))
    return delay * random.uniform(0.8, 1.2)


async def synthesize_one(
    text: str,
    voice: str,
    out_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    retries: int = DEFAULT_RETRIES,
) -> None:
    last_exc: BaseException | None = None
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(
                text, voice, rate=rate, volume=volume, pitch=pitch
            )
            await communicate.save(out_path)
            if attempt > 0:
                log_info(
                    f"EdgeTTS recovered voice={voice} attempt={attempt + 1}/{retries}"
                )
            return
        except _RETRYABLE_EXC as exc:
            last_exc = exc
            error_class = type(exc).__name__
            if attempt >= retries - 1:
                log_error(
                    f"EdgeTTS giving up voice={voice} attempt={attempt + 1}/{retries} error={error_class}: {exc}"
                )
                break
            retry_after = _retry_after_from_exc(exc)
            if retry_after is not None or _is_rate_limited(exc):
                base = retry_after if retry_after is not None else _DELAY_CAP
                delay = max(base, _compute_backoff(attempt))
            else:
                delay = _compute_backoff(attempt)
            log_error(
                f"EdgeTTS retryable voice={voice} attempt={attempt + 1}/{retries} "
                f"error={error_class}: {exc} delay_next={delay:.2f}s"
            )
            await asyncio.sleep(delay)
        except EdgeTTSException as exc:
            # Lỗi base khác (ít gặp): cho retry như nhánh retryable.
            last_exc = exc
            error_class = type(exc).__name__
            if attempt >= retries - 1:
                log_error(
                    f"EdgeTTS giving up voice={voice} attempt={attempt + 1}/{retries} error={error_class}: {exc}"
                )
                break
            delay = _compute_backoff(attempt)
            log_error(
                f"EdgeTTS retryable voice={voice} attempt={attempt + 1}/{retries} "
                f"error={error_class}: {exc} delay_next={delay:.2f}s"
            )
            await asyncio.sleep(delay)
        except Exception as exc:  # pragma: no cover - lỗi không phục hồi được
            log_error(
                f"EdgeTTS fatal voice={voice} attempt={attempt + 1} "
                f"error={type(exc).__name__}: {exc}"
            )
            raise
    raise RuntimeError(
        f"Khong the synthesize voice sau {retries} lan: {last_exc}"
    ) from last_exc


def synthesize_sync(
    text: str,
    voice: str,
    out_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    retries: int = DEFAULT_RETRIES,
) -> None:
    asyncio.run(
        synthesize_one(
            text=text,
            voice=voice,
            out_path=out_path,
            rate=rate,
            volume=volume,
            pitch=pitch,
            retries=retries,
        )
    )


async def synthesize_batch(
    jobs: list[TtsJob],
    concurrency: int,
    on_done: Callable[[TtsJob, bool, BaseException | None], Awaitable[None] | None],
    retries: int = DEFAULT_RETRIES,
) -> None:
    if not jobs:
        return
    concurrency = max(1, int(concurrency))
    semaphore = asyncio.Semaphore(concurrency)
    started_at = time.monotonic()
    log_info(
        f"Batch synth start concurrency={concurrency} targets={len(jobs)} retries={retries}"
    )

    ok_count = 0
    fail_count = 0

    async def _run_one(job: TtsJob) -> tuple[TtsJob, bool, BaseException | None]:
        async with semaphore:
            try:
                await synthesize_one(
                    text=job.text,
                    voice=job.voice,
                    out_path=job.out_path,
                    rate=job.rate,
                    volume=job.volume,
                    pitch=job.pitch,
                    retries=retries,
                )
                return job, True, None
            except BaseException as exc:  # noqa: BLE001
                return job, False, exc

    tasks = [asyncio.create_task(_run_one(job)) for job in jobs]
    try:
        for fut in asyncio.as_completed(tasks):
            job, ok, exc = await fut
            if ok:
                ok_count += 1
            else:
                fail_count += 1
            try:
                result = on_done(job, ok, exc)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as cb_exc:  # pragma: no cover - log và tiếp tục
                log_error(
                    f"Batch on_done callback failed segment={job.seg_index} error={cb_exc}"
                )
    finally:
        elapsed = time.monotonic() - started_at
        log_info(
            f"Batch synth done ok={ok_count} failed={fail_count} elapsed={elapsed:.2f}s"
        )


# Tương thích ngược: vài chỗ trong dự án có thể import `synthesize`.
async def synthesize(
    text: str,
    voice: str,
    out_path: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> None:
    await synthesize_one(
        text=text,
        voice=voice,
        out_path=out_path,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )
