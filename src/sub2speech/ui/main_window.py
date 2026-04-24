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
from sub2speech.ui.animated_progress import AnimatedProgressBar
from sub2speech.utils.i18n import LANG_EN, LANG_VI, tr, translator
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

        self.progress = AnimatedProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)

        self.audio_output = QAudioOutput(self)
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.9)
        self._active_preview_file: str | None = None

        self.header_status = QLabel(tr("status.no_file"))
        self.header_status.setObjectName("subtleText")
        self.open_file_button = QPushButton(tr("top.open_file"))
        self.open_file_button.clicked.connect(self.open_file)
        self.open_file_button.setMinimumWidth(120)
        self.open_file_button.setObjectName("primaryButton")
        self.language_button = QPushButton()
        self.language_button.setMinimumWidth(70)
        self.language_button.clicked.connect(self._toggle_language)
        self.help_button = QPushButton(tr("top.help"))
        self.help_button.clicked.connect(self.show_usage_guide)
        self.help_button.setMinimumWidth(100)

        self.player_status = QLabel(tr("player.status_idle"))
        self.player_time_label = QLabel("00:00 / 00:00")
        self.player_time_label.setObjectName("subtleText")
        self.player_duration_ms = 0
        self.player_slider = QSlider(Qt.Horizontal)
        self.player_slider.setRange(0, 0)
        self.play_button = QPushButton(tr("player.play"))
        self.stop_button = QPushButton(tr("player.stop"))
        self.play_button.clicked.connect(self._toggle_play_pause)
        self.stop_button.clicked.connect(self.media_player.stop)
        self.player_slider.sliderMoved.connect(self._seek_position)
        self.subtitle_preview_button = QPushButton(tr("subtitle.preview_btn"))
        self.subtitle_preview_button.clicked.connect(self.preview_selected)
        self.subtitle_table.cellDoubleClicked.connect(self._preview_by_row)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        subtitles_panel = QFrame()
        subtitles_panel.setObjectName("contentCard")
        subtitles_layout = QVBoxLayout(subtitles_panel)
        subtitles_layout.setContentsMargins(12, 10, 12, 10)
        subtitles_toolbar = QHBoxLayout()
        subtitles_toolbar.setContentsMargins(0, 0, 0, 0)
        subtitles_toolbar.setSpacing(8)
        self.content_section_title = self._build_section_title(tr("section.content"))
        subtitles_toolbar.addWidget(self.content_section_title)
        subtitles_toolbar.addStretch(1)
        subtitles_toolbar.addWidget(self.subtitle_preview_button)
        subtitles_layout.addLayout(subtitles_toolbar)
        subtitles_layout.addWidget(self.subtitle_table)

        speaker_panel = QFrame()
        speaker_panel.setObjectName("configCard")
        speaker_layout = QVBoxLayout(speaker_panel)
        speaker_layout.setContentsMargins(12, 10, 12, 10)
        self.voice_section_title = self._build_section_title(tr("section.voice"))
        speaker_layout.addWidget(self.voice_section_title)
        speaker_layout.addWidget(self.speaker_manager)

        top_split = QSplitter()
        top_split.addWidget(subtitles_panel)
        top_split.addWidget(speaker_panel)
        top_split.setStretchFactor(0, 2)
        top_split.setStretchFactor(1, 1)
        top_split.setHandleWidth(6)
        top_split.setCollapsible(0, False)
        top_split.setCollapsible(1, False)
        top_split.setSizes([int(self.width() * 0.62), int(self.width() * 0.38)])

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)
        top_bar_card = QFrame()
        top_bar_card.setObjectName("topBarCard")
        top_bar_layout = QHBoxLayout(top_bar_card)
        top_bar_layout.setContentsMargins(12, 10, 12, 10)
        top_bar_layout.setSpacing(8)
        top_bar_layout.addWidget(self.open_file_button)
        top_bar_layout.addWidget(self.header_status, 1)
        top_bar_layout.addWidget(self.language_button)
        top_bar_layout.addWidget(self.help_button)
        root_layout.addWidget(top_bar_card)

        content_card = QFrame()
        content_card.setObjectName("contentCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.addWidget(top_split, 1)
        root_layout.addWidget(content_card, 1)

        bottom_card = QFrame()
        bottom_card.setObjectName("actionCard")
        bottom_layout = QVBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(12, 10, 12, 10)
        bottom_layout.setSpacing(8)
        bottom_layout.addWidget(self.output_panel)
        player_row = QHBoxLayout()
        player_row.addWidget(self.play_button)
        player_row.addWidget(self.stop_button)
        player_row.addWidget(self.player_slider, 1)
        player_row.addWidget(self.player_time_label)
        player_row.addWidget(self.player_status)
        bottom_layout.addLayout(player_row)
        bottom_layout.addWidget(self.progress)
        root_layout.addWidget(bottom_card)
        self.setCentralWidget(root)
        translator.language_changed.connect(self._on_language_changed)
        self.retranslate_ui()
        self._apply_tooltips()
        self._update_ui_state()

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("dlg.open_input_title"),
            "",
            tr("dlg.open_input_filter"),
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
            QMessageBox.critical(self, tr("dlg.error_title"), str(exc))
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
        else:
            self._seed_auto_speakers()
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
            QMessageBox.warning(self, tr("dlg.warn_title"), tr("subtitle.warn_select_row"))
            return
        seg = self.segments[row]
        voice = self._build_segment_voice_map().get(seg.index, "")
        if not voice:
            QMessageBox.warning(self, tr("dlg.warn_title"), tr("subtitle.warn_no_voice"))
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

    def _preview_by_row(self, row: int, _column: int) -> None:
        self.subtitle_table.selectRow(row)
        self.preview_selected()

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
            QMessageBox.warning(self, tr("dlg.warn_title"), tr("dlg.no_input"))
            return
        output_dir = self.output_panel.output_edit.text().strip() or self.settings.output_dir
        if not output_dir:
            QMessageBox.warning(self, tr("dlg.warn_title"), tr("dlg.no_output_dir"))
            return
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        base_name = Path(self.input_path).stem if self.input_path else "output"
        output_path = str(Path(output_dir) / f"{base_name}.mp3")

        voice_map = self._build_segment_voice_map()
        option_map = self._build_segment_voice_options_map()
        missing = [seg.index for seg in self.segments if not voice_map.get(seg.index)]
        if missing:
            log_error(f"Export blocked missing_voice_segments={missing}")
            QMessageBox.warning(self, tr("dlg.missing_voice_title"), tr("dlg.missing_voice_msg", items=", ".join(map(str, missing))))
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
        self.progress.setVisible(False)
        self.pending_failed_segments = []
        log_info(f"Export done path={path}")
        QMessageBox.information(self, tr("dlg.done_title"), tr("dlg.export_done", path=path))
        self._play_audio_file(path)
        self._update_ui_state()

    def _on_export_incomplete(self, failed_segments: object) -> None:
        self.progress.setVisible(False)
        failed_list = sorted(int(x) for x in (failed_segments or []))
        self.pending_failed_segments = failed_list
        log_error(f"Export incomplete failed_segments={failed_list}")
        QMessageBox.warning(
            self,
            tr("dlg.export_incomplete_title"),
            tr("dlg.export_incomplete_msg", items=", ".join(str(i) for i in failed_list)),
        )
        self._update_ui_state()

    def _on_export_error(self, message: str) -> None:
        self.progress.setVisible(False)
        log_error(f"Export error: {message}")
        QMessageBox.critical(self, tr("dlg.error_title"), message)
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
        QMessageBox.critical(self, tr("dlg.preview_error_title"), message)

    def _open_audio_file(self, path: str) -> None:
        url = QUrl.fromLocalFile(str(Path(path).resolve()))
        QDesktopServices.openUrl(url)

    def _play_audio_file(self, path: str) -> None:
        resolved = str(Path(path).resolve())
        self.player_status.setText(tr("player.status_playing", name=Path(path).name))
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
        self._update_player_time_label(position)

    def _on_duration_changed(self, duration: int) -> None:
        self.player_duration_ms = max(duration, 0)
        self.player_slider.setRange(0, max(duration, 0))
        self._update_player_time_label(self.media_player.position())

    def _on_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText(tr("player.pause"))
        else:
            self.play_button.setText(tr("player.play"))

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
        self.output_panel.export_button.setToolTip(tr("tip.export"))
        self.subtitle_preview_button.setToolTip(tr("tip.preview_row"))
        self.speaker_manager.rate_input.setToolTip(tr("tip.rate"))
        self.speaker_manager.volume_input.setToolTip(tr("tip.volume"))
        self.speaker_manager.pitch_input.setToolTip(tr("tip.pitch"))

    def _update_header_status(self) -> None:
        if not self.input_path:
            self.header_status.setText(tr("status.no_file"))
            return
        file_name = Path(self.input_path).name
        self.header_status.setText(tr("status.file_info", file=file_name, mode=self._current_mode_text(), count=len(self.segments)))

    def _update_ui_state(self) -> None:
        has_segments = bool(self.segments)
        has_mapping = all(bool(self._build_segment_voice_map().get(seg.index, "")) for seg in self.segments) if has_segments else False
        self.subtitle_preview_button.setEnabled(has_segments)
        self.output_panel.export_button.setEnabled(has_segments and has_mapping)
        self._refresh_export_button_label()
        self._update_header_status()

    def _refresh_export_button_label(self) -> None:
        if self.pending_failed_segments:
            self.output_panel.export_button.setText(tr("output.export_retry"))
            self.output_panel.export_button.setToolTip(tr("tip.export_retry"))
        else:
            self.output_panel.export_button.setText(tr("output.export"))
            self.output_panel.export_button.setToolTip(tr("tip.export"))

    def show_usage_guide(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("help.dialog_title"))
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)
        text = QTextEdit(dialog)
        text.setReadOnly(True)
        text.setHtml(
            tr("help.html_body").format(
                version=__version__,
                settings_path=self.config.settings_path,
                output_dir=self.settings.output_dir,
            )
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

    def _current_mode_text(self) -> str:
        if self.current_input_mode == "TXT":
            return tr("status.mode_txt")
        if self.current_input_mode == "SRT":
            return tr("status.mode_srt")
        return tr("status.mode_unknown")

    def _toggle_language(self) -> None:
        new_lang = LANG_EN if translator.language == LANG_VI else LANG_VI
        self.settings.language = new_lang
        self.config.save_settings(self.settings)
        translator.set_language(new_lang)

    def _on_language_changed(self, _language: str) -> None:
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.open_file_button.setText(tr("top.open_file"))
        self.help_button.setText(tr("top.help"))
        self.language_button.setText(tr("top.lang_toggle_to_en") if translator.language == LANG_VI else tr("top.lang_toggle_to_vi"))
        self.play_button.setText(tr("player.play"))
        self.stop_button.setText(tr("player.stop"))
        if self.media_player.playbackState() != QMediaPlayer.PlayingState:
            self.player_status.setText(tr("player.status_idle"))
        self.subtitle_preview_button.setText(tr("subtitle.preview_btn"))
        self.content_section_title.setText(tr("section.content"))
        self.voice_section_title.setText(tr("section.voice"))
        self.speaker_manager.retranslate_ui()
        self.output_panel.retranslate_ui()
        self.subtitle_table.retranslate_headers()
        self._apply_tooltips()
        self._update_ui_state()

    def _update_player_time_label(self, position_ms: int) -> None:
        self.player_time_label.setText(
            f"{self._format_time(position_ms)} / {self._format_time(self.player_duration_ms)}"
        )

    def _format_time(self, milliseconds: int) -> str:
        total_seconds = max(milliseconds, 0) // 1000
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"
