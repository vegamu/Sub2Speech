import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from sub2speech.config import AppConfig
from sub2speech.core.audio_processor import (
    build_timeline_audio,
    concatenate_audio_files_to_mp3,
    export_single_mp3,
)
from sub2speech.core.edge_tts_engine import TtsJob, synthesize_batch
from sub2speech.models.subtitle import Segment
from sub2speech.utils.logging_utils import log_error, log_info


class TtsWorker(QThread):
    progress = Signal(int)
    segment_done = Signal(int, str)
    finished = Signal(str)
    incomplete = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        config: AppConfig,
        source_name: str,
        source_file_name: str,
        source_md5: str,
        segments: list[Segment],
        segment_voice_map: dict[int, str],
        segment_option_map: dict[int, dict[str, str]],
        output_path: str,
        save_original: bool,
        retry_only_indices: list[int] | None = None,
        is_text_input: bool = False,
    ) -> None:
        super().__init__()
        self.config = config
        self.source_name = source_name
        self.source_file_name = source_file_name
        self.source_md5 = source_md5
        self.segments = segments
        self.segment_voice_map = segment_voice_map
        self.segment_option_map = segment_option_map
        self.output_path = output_path
        self.save_original = save_original
        self.retry_only_indices = retry_only_indices or []
        self.is_text_input = is_text_input

    def run(self) -> None:
        try:
            log_info(
                f"Export start source={self.source_name} md5={self.source_md5} segments={len(self.segments)} output={self.output_path} save_original={self.save_original}"
            )
            sessions_root = Path(self.config.temp_dir) / "export_sessions"
            session_key = f"{self.source_name}_{self.source_md5}"
            session_dir = sessions_root / session_key
            session_dir.mkdir(parents=True, exist_ok=True)
            self._update_registry(
                sessions_root,
                session_key,
                status="running",
                session_dir=session_dir,
            )
            targets = self._collect_targets()
            total = max(len(targets), 1)
            failed_segments: list[int] = []

            original_dir = Path(self.config.audio_root) / self.source_name
            if self.save_original:
                original_dir.mkdir(parents=True, exist_ok=True)

            processed_count = 0
            jobs: list[TtsJob] = []
            for seg in targets:
                voice = self.segment_voice_map.get(seg.index, "")
                if not voice:
                    failed_segments.append(seg.index)
                    log_error(f"Skip synth segment={seg.index} reason=no_voice")
                    processed_count += 1
                    self.progress.emit(int((processed_count / total) * 80))
                    continue
                options = self.segment_option_map.get(
                    seg.index,
                    {"rate": "+0%", "volume": "+0%", "pitch": "+0Hz"},
                )
                out_raw = session_dir / f"segment_{seg.index:04d}.mp3"
                log_info(
                    f"Queue synth segment={seg.index} voice={voice} rate={options['rate']} volume={options['volume']} pitch={options['pitch']}"
                )
                jobs.append(
                    TtsJob(
                        seg_index=seg.index,
                        text=seg.text,
                        voice=voice,
                        out_path=str(out_raw),
                        rate=options.get("rate", "+0%"),
                        volume=options.get("volume", "+0%"),
                        pitch=options.get("pitch", "+0Hz"),
                    )
                )

            async def _on_done(
                job: TtsJob,
                ok: bool,
                segment_exc: BaseException | None,
            ) -> None:
                nonlocal processed_count
                try:
                    if ok:
                        if self.save_original:
                            file_name = Path(job.out_path).name
                            shutil.copy2(job.out_path, str(original_dir / file_name))
                            log_info(f"Saved original segment file={original_dir / file_name}")
                        self.segment_done.emit(job.seg_index, job.out_path)
                    else:
                        failed_segments.append(job.seg_index)
                        log_error(f"Segment synth failed segment={job.seg_index}: {segment_exc}")
                finally:
                    processed_count += 1
                    self.progress.emit(int((processed_count / total) * 80))

            if jobs:
                settings = self.config.load_settings()
                raw_concurrency = getattr(settings, "tts_concurrency", 2)
                concurrency = max(1, min(int(raw_concurrency), 8))
                log_info(f"Start synth batch jobs={len(jobs)} concurrency={concurrency}")
                asyncio.run(
                    synthesize_batch(
                        jobs=jobs,
                        concurrency=concurrency,
                        on_done=_on_done,
                    )
                )
            else:
                log_info("No synth jobs queued")

            if failed_segments:
                failed_sorted = sorted(set(failed_segments))
                log_error(f"Synthesis incomplete failed_segments={failed_sorted}")
                self._update_registry(
                    sessions_root,
                    session_key,
                    status="incomplete",
                    session_dir=session_dir,
                    failed_segments=failed_sorted,
                )
                self.incomplete.emit(failed_sorted)
                return

            raw_paths = self._collect_all_segment_paths(session_dir)
            if len(self.segments) == 1:
                log_info("Single segment export mode")
                export_single_mp3(raw_paths[0], self.output_path)
            elif self.is_text_input:
                log_info("TXT sequential export mode")
                concatenate_audio_files_to_mp3(raw_paths, self.output_path)
            else:
                log_info("Timeline export mode")
                build_timeline_audio(self.segments, raw_paths, self.output_path, session_dir)

            self.progress.emit(100)
            log_info(f"Export completed output={self.output_path}")
            self._update_registry(
                sessions_root,
                session_key,
                status="completed",
                session_dir=session_dir,
                failed_segments=[],
            )
            # Xuất hoàn tất thì xóa session trung gian để tránh dùng nhầm ở lần sau.
            shutil.rmtree(session_dir, ignore_errors=True)
            self._update_registry(
                sessions_root,
                session_key,
                status="completed_cleaned",
                session_dir=session_dir,
                failed_segments=[],
            )
            self.finished.emit(self.output_path)
        except Exception as exc:
            log_error(f"Export failed: {exc}")
            self.error.emit(str(exc))

    def _collect_targets(self) -> list[Segment]:
        if not self.retry_only_indices:
            return list(self.segments)
        retry_set = set(self.retry_only_indices)
        return [seg for seg in self.segments if seg.index in retry_set]

    def _collect_all_segment_paths(self, session_dir: Path) -> list[str]:
        paths: list[str] = []
        missing: list[int] = []
        for seg in self.segments:
            file_path = session_dir / f"segment_{seg.index:04d}.mp3"
            if not file_path.exists():
                missing.append(seg.index)
            paths.append(str(file_path))
        if missing:
            raise RuntimeError(
                f"Thieu file segment trung gian: {', '.join(str(item) for item in missing)}. "
                "Hay bam Xuat MP3 de tao lai cac segment loi."
            )
        return paths

    def _update_registry(
        self,
        sessions_root: Path,
        session_key: str,
        status: str,
        session_dir: Path,
        failed_segments: list[int] | None = None,
    ) -> None:
        registry_path = sessions_root / "sessions_index.json"
        sessions_root.mkdir(parents=True, exist_ok=True)
        try:
            if registry_path.exists():
                raw = json.loads(registry_path.read_text(encoding="utf-8"))
            else:
                raw = {}
        except Exception:
            raw = {}

        raw[session_key] = {
            "source_file_name": self.source_file_name,
            "source_name": self.source_name,
            "source_md5": self.source_md5,
            "session_dir": str(session_dir),
            "status": status,
            "failed_segments": failed_segments or [],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        registry_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
