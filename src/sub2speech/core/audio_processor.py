import shutil
import subprocess
import re
from pathlib import Path

import ffmpeg
import imageio_ffmpeg

from sub2speech.models.subtitle import Segment
from sub2speech.utils.logging_utils import log_info, log_error


def ffmpeg_cmd() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffprobe_duration(file_path: str) -> float:
    # Tránh phụ thuộc ffprobe riêng (dễ thiếu trên Windows khi dùng imageio-ffmpeg).
    # Dùng chính ffmpeg -i để đọc Duration từ stderr.
    cmd = [ffmpeg_cmd(), "-i", file_path, "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)", output)
    if not match:
        log_error(f"Cannot parse duration file={file_path}")
        return 0.0
    hh = int(match.group(1))
    mm = int(match.group(2))
    ss = float(match.group(3))
    return hh * 3600 + mm * 60 + ss


def _atempo_chain(factor: float) -> str:
    parts: list[str] = []
    remaining = factor
    while remaining > 2.0:
        parts.append("2.0")
        remaining /= 2.0
    parts.append(f"{remaining:.6f}")
    return ",".join([f"atempo={item}" for item in parts])


def _normalize_segment_duration(input_path: str, output_path: str, target_duration: float) -> None:
    log_info(f"Normalize segment input={input_path} output={output_path} target_duration={target_duration:.3f}")
    actual = _run_ffprobe_duration(input_path)
    if actual <= 0:
        raise RuntimeError(f"Khong doc duoc duration cua {input_path}")
    if target_duration <= 0:
        shutil.copy2(input_path, output_path)
        return

    if actual > target_duration + 0.05:
        speed = actual / target_duration
        try:
            ffmpeg.input(input_path).output(
                output_path,
                acodec="pcm_s16le",
                af=_atempo_chain(speed),
                ar=24000,
                ac=1,
            ).global_args("-y").run(cmd=ffmpeg_cmd(), quiet=True)
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
            log_error(f"FFmpeg normalize(speed-up) failed input={input_path} detail={stderr}")
            raise RuntimeError(f"FFmpeg normalize(speed-up) failed for {input_path}") from exc
    elif actual < target_duration - 0.05:
        pad = max(target_duration - actual, 0.0)
        try:
            ffmpeg.input(input_path).filter_("apad", pad_dur=pad).output(
                output_path,
                acodec="pcm_s16le",
                ar=24000,
                ac=1,
                t=target_duration,
            ).global_args("-y").run(cmd=ffmpeg_cmd(), quiet=True)
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
            log_error(f"FFmpeg normalize(pad) failed input={input_path} detail={stderr}")
            raise RuntimeError(f"FFmpeg normalize(pad) failed for {input_path}") from exc
    else:
        try:
            ffmpeg.input(input_path).output(
                output_path, acodec="pcm_s16le", ar=24000, ac=1
            ).global_args("-y").run(cmd=ffmpeg_cmd(), quiet=True)
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
            log_error(f"FFmpeg normalize(copy-like) failed input={input_path} detail={stderr}")
            raise RuntimeError(f"FFmpeg normalize(copy-like) failed for {input_path}") from exc


def export_single_mp3(input_path: str, output_path: str) -> None:
    try:
        ffmpeg.input(input_path).output(
            output_path, acodec="libmp3lame", audio_bitrate="192k", ar=24000, ac=1
        ).global_args("-y").run(cmd=ffmpeg_cmd(), quiet=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
        log_error(f"FFmpeg export single mp3 failed input={input_path} detail={stderr}")
        raise RuntimeError(f"FFmpeg export single mp3 failed for {input_path}") from exc


def concatenate_audio_files_to_mp3(input_paths: list[str], output_path: str) -> None:
    if not input_paths:
        raise RuntimeError("Khong co file audio de concatenate")
    if len(input_paths) == 1:
        export_single_mp3(input_paths[0], output_path)
        return
    try:
        streams = [ffmpeg.input(path).audio for path in input_paths]
        joined = ffmpeg.concat(*streams, v=0, a=1).node[0]
        ffmpeg.output(
            joined,
            output_path,
            acodec="libmp3lame",
            audio_bitrate="192k",
            ar=24000,
            ac=1,
        ).global_args("-y").run(cmd=ffmpeg_cmd(), quiet=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
        log_error(f"FFmpeg concatenate txt segments failed detail={stderr}")
        raise RuntimeError("FFmpeg concatenate txt segments failed") from exc


def build_timeline_audio(
    segments: list[Segment],
    segment_audio_paths: list[str],
    out_mp3: str,
    temp_dir: Path,
) -> None:
    log_info(f"Build timeline start segments={len(segments)} out={out_mp3}")
    if len(segments) != len(segment_audio_paths):
        raise ValueError("So segment va so file audio khong khop")

    adjusted_paths: list[tuple[str, int]] = []
    for idx, (seg, in_path) in enumerate(zip(segments, segment_audio_paths), start=1):
        start_sec = _parse_time(seg.start)
        end_sec = _parse_time(seg.end)
        target_duration = max(end_sec - start_sec, 0.01)
        adjusted_path = temp_dir / f"adjusted_{idx:04d}.wav"
        _normalize_segment_duration(in_path, str(adjusted_path), target_duration)
        adjusted_paths.append((str(adjusted_path), int(start_sec * 1000)))

    total_duration = max(_parse_time(seg.end) for seg in segments) + 0.2
    base_silence = temp_dir / "base_silence.wav"
    try:
        ffmpeg.input("anullsrc=r=24000:cl=mono", f="lavfi", t=total_duration).output(
            str(base_silence), acodec="pcm_s16le", ar=24000, ac=1
        ).global_args("-y").run(cmd=ffmpeg_cmd(), quiet=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
        log_error(f"FFmpeg create base silence failed detail={stderr}")
        raise RuntimeError("FFmpeg create base silence failed") from exc

    streams = [ffmpeg.input(str(base_silence)).audio]
    for path, delay_ms in adjusted_paths:
        delayed = ffmpeg.input(path).audio.filter_("adelay", f"{delay_ms}|{delay_ms}")
        streams.append(delayed)

    mixed = ffmpeg.filter(streams, "amix", inputs=len(streams), duration="longest", dropout_transition=0)
    try:
        ffmpeg.output(mixed, out_mp3, acodec="libmp3lame", audio_bitrate="192k", ar=24000, ac=1).global_args(
            "-y"
        ).run(cmd=ffmpeg_cmd(), quiet=True)
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="ignore") if exc.stderr else str(exc)
        log_error(f"FFmpeg mix timeline failed detail={stderr}")
        raise RuntimeError("FFmpeg mix timeline failed") from exc
    log_info(f"Build timeline done out={out_mp3}")


def _parse_time(value: str) -> float:
    hh, mm, sec_msec = value.split(":")
    sec, msec = sec_msec.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(sec) + int(msec) / 1000.0
