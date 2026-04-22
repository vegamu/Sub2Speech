import hashlib
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sub2speech.config import AppConfig, Settings
from sub2speech import __version__
from sub2speech.core.subtitle_parser import parse_input_file
from sub2speech.core.voices_catalog import get_grouped_voices
from sub2speech.models.speaker import Speaker
from sub2speech.models.subtitle import Segment
from sub2speech.ui.output_panel import OutputPanel
from sub2speech.ui.speaker_manager import SpeakerManager
from sub2speech.ui.subtitle_table import SubtitleTable
from sub2speech.ui.theme import build_stylesheet
from sub2speech.utils.logging_utils import log_error, log_info
from sub2speech.workers.preview_worker import PreviewWorker
from sub2speech.workers.tts_worker import TtsWorker


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.settings: Settings = self.config.load_settings()
        self.segments: list[Segment] = []
        self.input_path = ""
        self.current_input_mode = "NONE"
        self.voice_groups = get_grouped_voices(self.config.voices_cache_path)
        log_info(f"Loaded voice groups count={len(self.voice_groups)}")
        self.pending_failed_segments: list[int] = []
        self.last_export_base_name: str = ""
        self.input_md5: str = ""

        self.setWindowTitle("Sub2Speech")
        self.resize(1280, 720)
        self.setStyleSheet(build_stylesheet())

        self.subtitle_table = SubtitleTable()
        self.speaker_manager = SpeakerManager()
        self.speaker_manager.speakers_changed.connect(self.refresh_table)
        self.speaker_manager.preview_voice_requested.connect(self.preview_custom_voice)
        self.speaker_manager.set_voice_groups(self.voice_groups, self.settings.last_language_group)
        self.output_panel = OutputPanel()
        self.output_panel.output_edit.setText(self.settings.output_dir)
        self.output_panel.save_original_checkbox.setChecked(self.settings.save_original_audio)
        self.output_panel.export_button.clicked.connect(self.export_audio)
        self.output_panel.preview_button.clicked.connect(self.preview_selected)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)

        self.audio_output = QAudioOutput(self)
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.9)
        self._active_preview_file: str | None = None

        self.header_status = QLabel("Chưa chọn file phụ đề/văn bản.")
        self.header_status.setObjectName("subtleText")
        self.mode_hint = QLabel("")
        self.mode_hint.setObjectName("subtleText")
        self.open_file_button = QPushButton("Chọn file phụ đề/văn bản")
        self.open_file_button.clicked.connect(self.open_file)
        self.open_file_button.setFixedWidth(200)
        self.open_file_button.setObjectName("primaryButton")
        self.help_button = QPushButton("Trợ giúp")
        self.help_button.clicked.connect(self.show_usage_guide)
        self.help_button.setFixedWidth(110)

        self.player_status = QLabel("Trình phát: Chưa phát")
        self.player_slider = QSlider(Qt.Horizontal)
        self.player_slider.setRange(0, 0)
        self.play_button = QPushButton("Phát")
        self.stop_button = QPushButton("Dừng")
        self.play_button.clicked.connect(self._toggle_play_pause)
        self.stop_button.clicked.connect(self.media_player.stop)
        self.player_slider.sliderMoved.connect(self._seek_position)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        subtitles_panel = QFrame()
        subtitles_panel.setObjectName("contentCard")
        subtitles_layout = QVBoxLayout(subtitles_panel)
        subtitles_layout.setContentsMargins(8, 8, 8, 8)
        subtitles_layout.addWidget(self._build_section_title("Nội dung"))
        subtitles_layout.addWidget(self.subtitle_table)

        speaker_panel = QFrame()
        speaker_panel.setObjectName("configCard")
        speaker_layout = QVBoxLayout(speaker_panel)
        speaker_layout.setContentsMargins(8, 8, 8, 8)
        speaker_layout.addWidget(self._build_section_title("Chọn giọng đọc"))
        speaker_layout.addWidget(self.speaker_manager)

        top_split = QSplitter()
        top_split.addWidget(subtitles_panel)
        top_split.addWidget(speaker_panel)
        top_split.setStretchFactor(0, 2)
        top_split.setStretchFactor(1, 1)
        top_split.setSizes([820, 420])

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)
        top_bar_card = QFrame()
        top_bar_card.setObjectName("topBarCard")
        top_bar_layout = QVBoxLayout(top_bar_card)
        top_bar_layout.setContentsMargins(10, 8, 10, 8)
        top_bar_layout.setSpacing(4)
        top_actions = QHBoxLayout()
        top_actions.addWidget(self.open_file_button)
        top_actions.addStretch(1)
        top_actions.addWidget(self.help_button)
        top_bar_layout.addLayout(top_actions)
        top_bar_layout.addWidget(self.header_status)
        top_bar_layout.addWidget(self.mode_hint)
        root_layout.addWidget(top_bar_card)

        content_card = QFrame()
        content_card.setObjectName("contentCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.addWidget(top_split, 1)
        root_layout.addWidget(content_card, 1)

        action_card = QFrame()
        action_card.setObjectName("actionCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(8, 6, 8, 6)
        action_layout.addWidget(self.output_panel)
        root_layout.addWidget(action_card)

        player_card = QFrame()
        player_card.setObjectName("playerCard")
        player_layout = QVBoxLayout(player_card)
        player_layout.setContentsMargins(8, 6, 8, 6)
        player_row = QHBoxLayout()
        player_row.addWidget(self.player_status)
        player_row.addWidget(self.player_slider, 1)
        player_row.addWidget(self.play_button)
        player_row.addWidget(self.stop_button)
        player_layout.addLayout(player_row)
        root_layout.addWidget(player_card)
        root_layout.addWidget(self.progress)
        self.setCentralWidget(root)
        self._apply_tooltips()
        self._update_ui_state()

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file phụ đề hoặc văn bản",
            "",
            "Subtitle/Text (*.srt *.txt)",
        )
        if not file_path:
            return
        try:
            log_info(f"Open input file path={file_path}")
            self.segments = parse_input_file(file_path)
            if not self.segments:
                raise ValueError("File khong co noi dung hop le")
            log_info(f"Parsed input segments={len(self.segments)}")
        except Exception as exc:
            log_error(f"Open file failed: {exc}")
            QMessageBox.critical(self, "Lỗi", str(exc))
            return

        self.input_path = file_path
        self.current_input_mode = "TXT" if file_path.lower().endswith(".txt") else "SRT"
        self.input_md5 = self._compute_md5(file_path)
        log_info(f"Input file md5={self.input_md5}")
        self.pending_failed_segments = []
        self.speaker_manager.speakers.clear()
        self.speaker_manager.set_max_index(len(self.segments))
        is_txt = file_path.lower().endswith(".txt")
        self.speaker_manager.set_txt_mode(is_txt)
        if is_txt:
            # TXT mode: không cần tạo người nói/đoạn thủ công.
            self.speaker_manager.apply_txt_voice_settings()
            self.mode_hint.setText("Chế độ TXT: chỉ chọn giọng và tham số, hệ thống áp dụng toàn bộ nội dung.")
        else:
            self._seed_auto_speakers()
            self.mode_hint.setText("Chế độ SRT: gán giọng theo người nói hoặc theo nhóm đoạn.")
        self.refresh_table()
        self._update_header_status()
        self._update_ui_state()

    def _seed_auto_speakers(self) -> None:
        temp: dict[str, set[int]] = {}
        for seg in self.segments:
            if seg.speaker:
                temp.setdefault(seg.speaker, set()).add(seg.index)
        for name, values in temp.items():
            speaker = Speaker(name=name, segments=values)
            self.speaker_manager.speakers[name] = speaker
        if temp:
            log_info(f"Auto-seeded speakers count={len(temp)}")
        self.speaker_manager.refresh()

    def _build_segment_voice_map(self) -> dict[int, str]:
        voice_map: dict[int, str] = {}
        for speaker in self.speaker_manager.speakers.values():
            if not speaker.voice:
                continue
            for seg_index in speaker.segments:
                voice_map[seg_index] = speaker.voice
        for seg in self.segments:
            voice_map.setdefault(seg.index, "")
        return voice_map

    def _build_segment_voice_options_map(self) -> dict[int, dict[str, str]]:
        option_map: dict[int, dict[str, str]] = {}
        for speaker in self.speaker_manager.speakers.values():
            payload = {
                "rate": speaker.rate or "+0%",
                "volume": speaker.volume or "+0%",
                "pitch": speaker.pitch or "+0Hz",
            }
            for seg_index in speaker.segments:
                option_map[seg_index] = payload
        return option_map

    def refresh_table(self) -> None:
        self.subtitle_table.set_segments(
            self.segments,
            self._build_segment_voice_map(),
            self._build_segment_speaker_map(),
        )
        self._update_ui_state()

    def _build_segment_speaker_map(self) -> dict[int, str]:
        speaker_map: dict[int, str] = {}
        for speaker in self.speaker_manager.speakers.values():
            for seg_index in speaker.segments:
                speaker_map[seg_index] = speaker.name
        return speaker_map

    def preview_selected(self) -> None:
        row = self.subtitle_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Cảnh báo", "Hãy chọn 1 dòng phụ đề để nghe thử")
            return
        seg = self.segments[row]
        voice = self._build_segment_voice_map().get(seg.index, "")
        if not voice:
            QMessageBox.warning(self, "Cảnh báo", "Dòng này chưa có giọng đọc")
            return
        options = self._build_segment_voice_options_map().get(
            seg.index,
            {"rate": "+0%", "volume": "+0%", "pitch": "+0Hz"},
        )
        text = seg.text[:140]
        self.preview_worker = PreviewWorker(
            self.config,
            text,
            voice,
            rate=options["rate"],
            volume=options["volume"],
            pitch=options["pitch"],
        )
        log_info(
            f"Preview selected segment={seg.index} voice={voice} rate={options['rate']} volume={options['volume']} pitch={options['pitch']}"
        )
        self.preview_worker.finished.connect(self._play_audio_file)
        self.preview_worker.error.connect(self._on_preview_error)
        self.preview_worker.start()

    def preview_custom_voice(self, text: str, voice: str, rate: str, volume: str, pitch: str) -> None:
        self.preview_worker = PreviewWorker(
            self.config,
            text,
            voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
        log_info(f"Preview custom voice={voice} rate={rate} volume={volume} pitch={pitch}")
        self.preview_worker.finished.connect(self._play_audio_file)
        self.preview_worker.error.connect(self._on_preview_error)
        self.preview_worker.start()

    def export_audio(self) -> None:
        if not self.segments:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu đầu vào")
            return
        output_dir = self.output_panel.output_edit.text().strip() or self.settings.output_dir
        if not output_dir:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn thư mục xuất")
            return
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        base_name = Path(self.input_path).stem if self.input_path else "output"
        output_path = str(Path(output_dir) / f"{base_name}.mp3")

        voice_map = self._build_segment_voice_map()
        option_map = self._build_segment_voice_options_map()
        missing = [seg.index for seg in self.segments if not voice_map.get(seg.index)]
        if missing:
            log_error(f"Export blocked missing_voice_segments={missing}")
            QMessageBox.warning(self, "Thiếu voice", f"Các đoạn chưa có voice: {', '.join(map(str, missing))}")
            return

        self.settings.output_dir = output_dir
        self.settings.save_original_audio = self.output_panel.save_original_checkbox.isChecked()
        self.settings.last_language_group = self.speaker_manager.current_language_group()
        self.config.save_settings(self.settings)
        self.last_export_base_name = base_name

        self.progress.setVisible(True)
        self.progress.setValue(0)
        retry_only = self._resolve_retry_indices()
        self.worker = TtsWorker(
            config=self.config,
            source_name=base_name,
            source_file_name=Path(self.input_path).name if self.input_path else "",
            source_md5=self.input_md5 or "unknown",
            segments=self.segments,
            segment_voice_map=voice_map,
            segment_option_map=option_map,
            output_path=output_path,
            save_original=self.output_panel.save_original_checkbox.isChecked(),
            retry_only_indices=retry_only,
            is_text_input=self.input_path.lower().endswith(".txt") if self.input_path else False,
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_export_done)
        self.worker.incomplete.connect(self._on_export_incomplete)
        self.worker.error.connect(self._on_export_error)
        if retry_only:
            log_info(f"Retry failed segments={retry_only} output={output_path}")
        else:
            log_info(f"Starting export output={output_path}")
        self.worker.start()
        self._update_ui_state()

    def _on_export_done(self, path: str) -> None:
        self.progress.setValue(100)
        self.pending_failed_segments = []
        log_info(f"Export done path={path}")
        QMessageBox.information(self, "Hoàn tất", f"Đã xuất audio: {path}")
        self._play_audio_file(path)
        self._update_ui_state()

    def _on_export_incomplete(self, failed_segments: object) -> None:
        self.progress.setVisible(False)
        failed_list = sorted(int(x) for x in (failed_segments or []))
        self.pending_failed_segments = failed_list
        log_error(f"Export incomplete failed_segments={failed_list}")
        QMessageBox.warning(
            self,
            "Tạo audio chưa hoàn tất",
            "Các segment sau bị lỗi và đã được bỏ qua:\n"
            f"{', '.join(str(i) for i in failed_list)}\n\n"
            "Hãy chỉnh lại voice/tham số nếu cần, sau đó bấm 'Xuất MP3' để tạo lại segment lỗi. "
            "Khi không còn lỗi hệ thống sẽ tự render file cuối.",
        )
        self._update_ui_state()

    def _on_export_error(self, message: str) -> None:
        self.progress.setVisible(False)
        log_error(f"Export error: {message}")
        QMessageBox.critical(self, "Lỗi", message)
        self._update_ui_state()

    def _resolve_retry_indices(self) -> list[int]:
        if not self.pending_failed_segments:
            return []
        valid = sorted(seg.index for seg in self.segments if seg.index in set(self.pending_failed_segments))
        return valid

    def _compute_md5(self, file_path: str) -> str:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                md5.update(chunk)
        return md5.hexdigest()

    def _on_preview_error(self, message: str) -> None:
        log_error(f"Preview error: {message}")
        QMessageBox.critical(self, "Lỗi preview", message)

    def _open_audio_file(self, path: str) -> None:
        url = QUrl.fromLocalFile(str(Path(path).resolve()))
        QDesktopServices.openUrl(url)

    def _play_audio_file(self, path: str) -> None:
        resolved = str(Path(path).resolve())
        self.player_status.setText(f"Trình phát: {Path(path).name}")
        log_info(f"Play in-app file={resolved}")
        self._cleanup_active_preview_file()
        # Reset source để tránh cache media cũ khi preview liên tục.
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.media_player.setSource(QUrl.fromLocalFile(resolved))
        self._active_preview_file = self._resolve_preview_file_if_needed(resolved)
        self.media_player.play()

    def _toggle_play_pause(self) -> None:
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _seek_position(self, value: int) -> None:
        self.media_player.setPosition(value)

    def _on_position_changed(self, position: int) -> None:
        self.player_slider.blockSignals(True)
        self.player_slider.setValue(position)
        self.player_slider.blockSignals(False)

    def _on_duration_changed(self, duration: int) -> None:
        self.player_slider.setRange(0, max(duration, 0))

    def _on_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("Tạm dừng")
        else:
            self.play_button.setText("Phát")

    def _on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia:
            self._cleanup_active_preview_file()

    def _resolve_preview_file_if_needed(self, file_path: str) -> str | None:
        path = Path(file_path)
        try:
            is_temp = path.parent.resolve() == Path(self.config.temp_dir).resolve()
        except OSError:
            is_temp = False
        if is_temp and path.name.startswith("preview_") and path.suffix.lower() == ".mp3":
            return str(path)
        return None

    def _cleanup_active_preview_file(self) -> None:
        if not self._active_preview_file:
            return
        preview_path = Path(self._active_preview_file)
        self._active_preview_file = None
        try:
            if preview_path.exists():
                preview_path.unlink()
                log_info(f"Deleted preview temp file={preview_path}")
        except Exception as exc:
            log_error(f"Delete preview temp file failed path={preview_path} error={exc}")

    def _apply_tooltips(self) -> None:
        self.output_panel.export_button.setToolTip("Xuất file âm thanh MP3 192 kbps.")
        self.output_panel.preview_button.setToolTip("Nghe thử dòng phụ đề đang chọn.")
        self.speaker_manager.rate_input.setToolTip("Tốc độ đọc. Ví dụ: +10% hoặc -15%.")
        self.speaker_manager.volume_input.setToolTip("Âm lượng đọc. Ví dụ: +0% hoặc -10%.")
        self.speaker_manager.pitch_input.setToolTip("Cao độ giọng. Ví dụ: +0Hz hoặc +20Hz.")

    def _update_header_status(self) -> None:
        if not self.input_path:
            self.header_status.setText("Chưa chọn file phụ đề/văn bản.")
            return
        file_name = Path(self.input_path).name
        self.header_status.setText(
            f"Tệp: {file_name} | Chế độ: {self.current_input_mode} | Đoạn: {len(self.segments)}"
        )

    def _update_ui_state(self) -> None:
        has_segments = bool(self.segments)
        has_mapping = all(bool(self._build_segment_voice_map().get(seg.index, "")) for seg in self.segments) if has_segments else False
        self.output_panel.preview_button.setEnabled(has_segments)
        self.output_panel.export_button.setEnabled(has_segments and has_mapping)
        self._update_header_status()

    def show_usage_guide(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Hướng dẫn sử dụng")
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)
        text = QTextEdit(dialog)
        text.setReadOnly(True)
        text.setHtml(
            "<h3>Hướng dẫn nhanh</h3>"
            "<ol>"
            "<li>Bấm <b>Chọn file phụ đề/văn bản</b> để nạp dữ liệu.</li>"
            "<li>Nếu là <b>SRT</b>: gán giọng theo người nói/đoạn.</li>"
            "<li>Nếu là <b>TXT</b>: chỉ cần chọn 1 giọng và tham số đọc.</li>"
            "<li>Dùng <b>Preview</b> để nghe thử trước khi xuất.</li>"
            "<li>Chọn thư mục xuất và bấm <b>Xuất MP3</b>.</li>"
            "<li>Nếu có segment lỗi, bấm xuất lại để tạo lại segment lỗi.</li>"
            "</ol>"
            "<h4>Mẹo tham số</h4>"
            "<ul>"
            "<li>Rate: +10% / -10%</li>"
            "<li>Volume: +0% / -10%</li>"
            "<li>Pitch: +0Hz / +20Hz</li>"
            "</ul>"
            "<h4>Thông tin ứng dụng</h4>"
            "<p><b>Sub2Speech</b> là công cụ chuyển nội dung SRT/TXT thành âm thanh MP3 "
            "dành cho quy trình sản xuất nội dung. Ứng dụng hỗ trợ preview trong app, "
            "xử lý retry segment lỗi và lưu cấu hình ổn định theo phiên làm việc.</p>"
            "<ul>"
            f"<li>Phiên bản: <b>{__version__}</b></li>"
            "<li>Công nghệ: PySide6, edge-tts, ffmpeg</li>"
            f"<li>Tệp cấu hình: {self.config.settings_path}</li>"
            f"<li>Thư mục xuất mặc định: {self.settings.output_dir}</li>"
            "</ul>"
        )
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _build_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label
