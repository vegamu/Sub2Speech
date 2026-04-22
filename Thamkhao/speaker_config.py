import os
import sys
import time
import tempfile
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QTextEdit, QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QProgressBar, QApplication, QFrame, QToolButton
)
from ui.widgets.app_card import AppCard
from ui.widgets.section_header import SectionHeader
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from config import config
from utils.subtitle_utils import SubtitleParser
from utils.audio_utils import AudioProcessor
from models.elevenlabs_model import ElevenLabsAPI
from models.gemini_model import GeminiTTS
from models.edge_tts_model import EdgeTTSModel

class SpeechGenerationWorker(QThread):
    """
    Worker thread để tạo giọng nói
    """
    progress = pyqtSignal(int)
    segment_finished = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, subtitles, voice_selections, output_path, save_original=True, tts_provider="ElevenLabs", subtitle_path=None):
        super().__init__()
        self.subtitles = subtitles
        self.voice_selections = voice_selections
        self.output_path = output_path
        self.save_original = save_original
        self.tts_provider = tts_provider
        self.subtitle_path = subtitle_path
        self.temp_files = []
        self.original_audio_dir = None

        # Tạo thư mục để lưu file âm thanh gốc nếu cần
        if self.save_original:
            import os
            from pathlib import Path

            # Tạo thư mục con trong output_dir với tên file (không có phần mở rộng)
            output_filename = os.path.basename(output_path)
            output_name = os.path.splitext(output_filename)[0]
            self.original_audio_dir = Path(config.output_dir) / output_name
            self.original_audio_dir.mkdir(exist_ok=True)

    def run(self):
        try:
            # Khởi tạo provider
            provider = (self.tts_provider or "ElevenLabs").strip()
            elevenlabs_api = None
            gemini_tts = None
            if provider == "ElevenLabs":
                api_key = config.get("elevenlabs_api_key", "")
                if not api_key:
                    self.error.emit("API key ElevenLabs chưa được cấu hình!")
                    return
                elevenlabs_api = ElevenLabsAPI(api_key=api_key)
                if not elevenlabs_api.check_api_key():
                    self.error.emit("API key ElevenLabs không hợp lệ!")
                    return
            elif provider == "Gemini":
                gemini_key = config.get("gemini_api_key", "")
                if not gemini_key:
                    self.error.emit("API key Gemini chưa được cấu hình!")
                    return
                gemini_tts = GeminiTTS(api_key=gemini_key)
                if not gemini_tts.check_api_key():
                    self.error.emit("API key Gemini không hợp lệ!")
                    return
            else:
                # Edge TTS không cần API key
                edge_model = EdgeTTSModel()

            # Tạo thư mục tạm
            temp_dir = config.temp_dir
            temp_dir.mkdir(exist_ok=True)

            # Tạo giọng nói cho từng đoạn phụ đề
            audio_files = []
            total_segments = len(self.subtitles)

            # Với ElevenLabs cần có voice cho từng đoạn
            if provider == "ElevenLabs":
                missing_voices = []
                for i, _ in enumerate(self.subtitles):
                    if i not in self.voice_selections:
                        missing_voices.append(i + 1)
                if missing_voices:
                    self.error.emit(f"Các đoạn phụ đề sau chưa có giọng nói: {', '.join(map(str, missing_voices))}!")
                    return

            # Tạo giọng nói cho từng đoạn phụ đề
            for i, subtitle in enumerate(self.subtitles):
                # Cập nhật tiến trình
                progress = int((i / total_segments) * 80)
                self.progress.emit(progress)

                # Lấy thông tin phụ đề
                text = subtitle['text']
                # KHÔNG giới hạn text cho file TXT khi tạo giọng nói chính thức
                voice_id = self.voice_selections.get(i, None)

                if provider == "ElevenLabs" and not voice_id:
                    self.error.emit(f"Không có giọng nói được chọn cho đoạn {i + 1}!")
                    return

                # Tạo file tạm
                # Ghi MP3 cho cả hai provider (Gemini đang trả MP3)
                temp_suffix = ".mp3"
                temp_mp3 = temp_dir / f"temp_raw_{i}{temp_suffix}"

                # Log thông tin tổng hợp trước khi gọi API
                try:
                    preview_text = (text[:60] + "...") if len(text) > 60 else text
                    print(f"[TTS] Provider={provider} segment={i+1}/{total_segments} voice={voice_id} len={len(text)} temp={temp_mp3}\n       text: {preview_text}")
                except Exception:
                    pass

                # Tạo giọng nói
                try:
                    if provider == "ElevenLabs":
                        result = elevenlabs_api.text_to_speech_with_retry(
                            text=text,
                            voice_id=voice_id,
                            output_path=str(temp_mp3)
                        )
                    elif provider == "Gemini":
                        result = gemini_tts.text_to_speech_with_retry(
                            text=text,
                            output_path=str(temp_mp3),
                            voice_name=voice_id if voice_id else None,
                            audio_format="MP3"
                        )
                    else:
                        # Edge TTS synthesize
                        result = EdgeTTSModel().synthesize(
                            text=text,
                            voice=voice_id or "vi-VN-NamMinhNeural",
                            output_path=str(temp_mp3)
                        )
                except Exception as _tts_e:
                    import traceback as _tb
                    print(f"[TTS][ERROR] Provider={provider} segment={i+1} exception: {_tts_e}")
                    _tb.print_exc()
                    self.error.emit(f"Lỗi khi tạo giọng nói cho đoạn {i + 1}: {_tts_e}")
                    return

                if not result:
                    print(f"[TTS][FAIL] Provider={provider} segment={i+1} không trả kết quả")
                    self.error.emit(f"Lỗi khi tạo giọng nói cho đoạn {i + 1}!")
                    return

                # Log file tạm tạo ra
                try:
                    import os as _os
                    size_b = _os.path.getsize(temp_mp3) if _os.path.exists(temp_mp3) else 0
                    print(f"[TTS][OK] Provider={provider} segment={i+1} file={temp_mp3} size={size_b} bytes")
                except Exception:
                    pass

                # Lưu file âm thanh gốc nếu cần
                if provider == "ElevenLabs" and self.save_original and self.original_audio_dir:
                    import shutil
                    original_file = self.original_audio_dir / f"segment_{i+1:03d}.mp3"
                    try:
                        shutil.copy2(str(temp_mp3), str(original_file))
                        print(f"Đã lưu file âm thanh gốc: {original_file}")
                    except Exception as e:
                        print(f"Lỗi khi lưu file âm thanh gốc: {e}")

                self.temp_files.append(str(temp_mp3))
                audio_files.append(str(temp_mp3))

                # Thông báo đoạn đã hoàn thành
                self.segment_finished.emit(i, str(temp_mp3))

            # Tạo file âm thanh với timeline chính xác
            self.progress.emit(85)

            if not audio_files:
                self.error.emit("Không có file âm thanh nào được tạo!")
                return

            # Tạo file âm thanh với timeline chính xác
            self.progress.emit(90)

            # Nếu chỉ có 1 đoạn (file TXT), chỉ cần copy file audio (giữ nguyên thời lượng từ API)
            if len(self.subtitles) == 1:
                import shutil
                try:
                    shutil.copy2(audio_files[0], self.output_path)
                    self.progress.emit(100)
                    self.finished.emit(self.output_path)
                    return
                except Exception as e:
                    self.error.emit(f"Lỗi khi copy file audio: {e}")
                    return

            # Lấy thời lượng tổng cộng từ đoạn phụ đề cuối cùng
            total_duration = SubtitleParser.time_to_seconds(self.subtitles[-1]['end']) + 1  # Thêm 1 giây để đảm bảo đủ thời lượng

            # Tạo file âm thanh với timeline chính xác
            if AudioProcessor.create_timeline_audio(self.subtitles, audio_files, self.output_path, total_duration):
                self.progress.emit(100)
                self.finished.emit(self.output_path)
            else:
                # Nếu phương thức mới thất bại, thử phương thức khác
                print("Không thể tạo file âm thanh với timeline chính xác, thử phương thức khác...")

                # Tạo file âm thanh tạm thời cho từng đoạn phụ đề
                adjusted_audio_files = []

                for i, (subtitle, audio_path) in enumerate(zip(self.subtitles, audio_files)):
                    # Lấy thời lượng âm thanh
                    actual_duration = AudioProcessor.get_audio_duration(audio_path)
                    subtitle_duration = SubtitleParser.time_to_seconds(subtitle['end']) - SubtitleParser.time_to_seconds(subtitle['start'])

                    # Tạo file tạm
                    temp_wav = temp_dir / f"temp_adjusted_{i}.wav"

                    # Điều chỉnh tốc độ âm thanh
                    if actual_duration > subtitle_duration:
                        # Nếu âm thanh dài hơn phụ đề, tăng tốc độ
                        speed_factor = actual_duration / subtitle_duration
                        AudioProcessor.adjust_audio_speed(audio_path, str(temp_wav), speed_factor)
                    else:
                        # Nếu âm thanh ngắn hơn phụ đề, thêm khoảng lặng
                        # Sử dụng ffmpeg để thêm khoảng lặng
                        import ffmpeg
                        (
                            ffmpeg
                            .input(audio_path)
                            .filter('apad', pad_dur=subtitle_duration - actual_duration)
                            .output(str(temp_wav), acodec='pcm_s16le', ar='44100', ac=2)
                            .global_args('-y')
                            .run(quiet=True, overwrite_output=True)
                        )

                    self.temp_files.append(str(temp_wav))
                    adjusted_audio_files.append(str(temp_wav))

                # Tạo file âm thanh cuối cùng
                if AudioProcessor.concatenate_audio_files(adjusted_audio_files, self.output_path):
                    self.progress.emit(100)
                    self.finished.emit(self.output_path)
                else:
                    self.error.emit("Lỗi khi ghép các file âm thanh!")

        except Exception as e:
            self.error.emit(f"Lỗi: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # Xóa các file tạm
            for file_path in self.temp_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Lỗi khi xóa file tạm {file_path}: {e}")

class SpeakerConfig(QWidget):
    """
    Giao diện cấu hình người nói
    """

    def __init__(self):
        super().__init__()

        # Khởi tạo biến
        self.subtitles = []
        self.subtitle_path = None
        self.voice_selections = {}  # {subtitle_index: voice_id}
        self.speaker_voice_map = {}  # {speaker_name: voice_id}
        self.speakers = set()  # Tập hợp các người nói duy nhất
        self.voices = []

        # Tạo giao diện
        self.init_ui()

        # Tải danh sách giọng nói
        self.load_voices()

    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        def _make_step_card(index: int, title: str, subtitle: str) -> AppCard:
            return AppCard(f"Bước {index} · {title}", subtitle, self)

        def _make_collapsible(title: str):
            toggle = QToolButton(self)
            toggle.setCheckable(True)
            toggle.setChecked(False)
            toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            toggle.setArrowType(Qt.RightArrow)
            toggle.setText(title)
            toggle.setStyleSheet(
                "QToolButton { border: none; font-weight: 600; color: #0F172A; padding: 4px 0; }"
            )

            content = QFrame(self)
            content.setFrameShape(QFrame.NoFrame)
            content.setVisible(False)

            def _on_toggle(expanded: bool):
                toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
                content.setVisible(expanded)

            toggle.toggled.connect(_on_toggle)
            return toggle, content

        main_layout.addWidget(
            SectionHeader(
                "Tạo giọng nói từ phụ đề",
                "ElevenLabs, Gemini TTS, Edge TTS — gán giọng theo từng người nói.",
                self,
            )
        )
        print("[UI] SpeakerConfig: redesign medium", flush=True)

        step1_card = _make_step_card(
            1,
            "Chọn file phụ đề/văn bản",
            "Nạp nguồn nội dung đầu vào để hệ thống nhận diện danh sách người nói và các đoạn phụ đề.",
        )
        step1_body = QWidget(self)
        step1_layout = QHBoxLayout(step1_body)
        step1_layout.setContentsMargins(0, 0, 0, 0)
        step1_layout.setSpacing(10)
        self.subtitle_path_label = QLabel("Chưa chọn file phụ đề hoặc văn bản")
        self.subtitle_path_label.setStyleSheet("color: #475569;")
        step1_layout.addWidget(self.subtitle_path_label, 1)

        load_subtitle_button = QPushButton("Chọn file phụ đề/văn bản")
        load_subtitle_button.clicked.connect(self.load_subtitle_file)
        step1_layout.addWidget(load_subtitle_button)
        step1_card.set_body(step1_body)

        advanced_toggle, advanced_frame = _make_collapsible("Cài đặt nâng cao")
        advanced_layout = QVBoxLayout(advanced_frame)
        advanced_layout.setContentsMargins(0, 6, 0, 0)
        advanced_layout.setSpacing(8)

        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Nhà cung cấp TTS:"))
        self.tts_provider_combo = QComboBox()
        self.tts_provider_combo.addItems(["ElevenLabs", "Gemini", "Edge TTS"])
        default_provider = config.get("tts_provider", "ElevenLabs")
        idx = self.tts_provider_combo.findText(default_provider)
        if idx >= 0:
            self.tts_provider_combo.setCurrentIndex(idx)
        def _on_tts_provider_changed(v):
            config.set("tts_provider", v)
            self.voice_selections.clear()
            self.speaker_voice_map.clear()
            self.load_voices()
        self.tts_provider_combo.currentTextChanged.connect(_on_tts_provider_changed)
        provider_row.addWidget(self.tts_provider_combo, 1)
        advanced_layout.addLayout(provider_row)

        language_row = QHBoxLayout()
        language_row.addWidget(QLabel("Ngôn ngữ (Edge TTS):"))
        self.edge_language_combo = QComboBox()
        edge_langs = [
            "",
            "vi-VN",
            "en-US",
            "en-GB",
            "ja-JP",
            "ko-KR",
            "zh-CN",
        ]
        self.edge_language_combo.addItems(edge_langs)
        saved_lang = config.get("edge_tts_language", "")
        idx_lang = self.edge_language_combo.findText(saved_lang)
        if idx_lang >= 0:
            self.edge_language_combo.setCurrentIndex(idx_lang)
        def _on_edge_lang_changed(v):
            config.set("edge_tts_language", v)
            if hasattr(self, 'tts_provider_combo') and self.tts_provider_combo.currentText() == "Edge TTS":
                self.load_voices()
        self.edge_language_combo.currentTextChanged.connect(_on_edge_lang_changed)
        language_row.addWidget(self.edge_language_combo, 1)
        advanced_layout.addLayout(language_row)

        voice_button_layout = QHBoxLayout()
        add_voice_button = QPushButton("Thêm giọng nói")
        add_voice_button.clicked.connect(self.add_voice)
        voice_button_layout.addWidget(add_voice_button)

        edit_voice_button = QPushButton("Sửa giọng nói")
        edit_voice_button.clicked.connect(self.edit_voice)
        voice_button_layout.addWidget(edit_voice_button)

        delete_voice_button = QPushButton("Xóa giọng nói")
        delete_voice_button.clicked.connect(self.delete_voice)
        voice_button_layout.addWidget(delete_voice_button)

        refresh_voices_button = QPushButton("Làm mới")
        refresh_voices_button.clicked.connect(self.refresh_voices)
        voice_button_layout.addWidget(refresh_voices_button)
        advanced_layout.addLayout(voice_button_layout)

        step2_card = _make_step_card(
            2,
            "Gán giọng nói cho người nói",
            "Cấu hình giọng theo từng người nói, sau đó áp dụng nhanh cho toàn bộ đoạn phụ đề.",
        )
        step2_body = QWidget(self)
        step2_layout = QVBoxLayout(step2_body)
        step2_layout.setContentsMargins(0, 0, 0, 0)
        step2_layout.setSpacing(10)

        speaker_label = QLabel("Danh sách người nói và giọng đã gán")
        speaker_label.setStyleSheet("color: #64748B;")
        step2_layout.addWidget(speaker_label)

        self.speaker_mapping_table = QTableWidget()
        self.speaker_mapping_table.setColumnCount(2)
        self.speaker_mapping_table.setHorizontalHeaderLabels(["Người nói", "Giọng nói"])
        self.speaker_mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.speaker_mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.speaker_mapping_table.verticalHeader().setVisible(False)
        self.speaker_mapping_table.verticalHeader().setDefaultSectionSize(40)
        font = self.speaker_mapping_table.font()
        font.setPointSize(font.pointSize() + 1)
        self.speaker_mapping_table.setFont(font)
        step2_layout.addWidget(self.speaker_mapping_table, 1)

        speaker_button_layout = QHBoxLayout()
        speaker_button_layout.setSpacing(8)

        add_speaker_button = QPushButton("Thêm người nói")
        add_speaker_button.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; padding: 8px 12px; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        add_speaker_button.setMinimumHeight(40)
        add_speaker_button.clicked.connect(self.add_speaker)
        speaker_button_layout.addWidget(add_speaker_button)

        edit_speaker_button = QPushButton("Sửa người nói")
        edit_speaker_button.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; padding: 8px 12px; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background-color: #27ae60; }"
        )
        edit_speaker_button.setMinimumHeight(40)
        edit_speaker_button.clicked.connect(self.edit_speaker)
        speaker_button_layout.addWidget(edit_speaker_button)

        apply_button = QPushButton("Áp dụng cho tất cả đoạn")
        apply_button.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; padding: 8px 12px; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        apply_button.setMinimumHeight(40)
        apply_button.clicked.connect(self.apply_speaker_voices)
        speaker_button_layout.addWidget(apply_button)
        speaker_button_layout.addStretch(1)

        step2_layout.addLayout(speaker_button_layout)
        step2_card.set_body(step2_body)

        top_row_widget = QWidget(self)
        top_row_layout = QHBoxLayout(top_row_widget)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(12)

        left_col_widget = QWidget(top_row_widget)
        left_col_layout = QVBoxLayout(left_col_widget)
        left_col_layout.setContentsMargins(0, 0, 0, 0)
        left_col_layout.setSpacing(10)
        left_col_layout.addWidget(step1_card)
        left_col_layout.addWidget(advanced_toggle)
        left_col_layout.addWidget(advanced_frame)
        left_col_layout.addStretch(1)

        top_row_layout.addWidget(left_col_widget, 1)
        top_row_layout.addWidget(step2_card, 1)
        main_layout.addWidget(top_row_widget)

        subtitles_card = AppCard(
            "Danh sách phụ đề/văn bản",
            "Xem nhanh tất cả đoạn và giọng đã gán trước khi xuất âm thanh.",
            self,
        )
        subtitles_body = QWidget(self)
        subtitles_body_layout = QVBoxLayout(subtitles_body)
        subtitles_body_layout.setContentsMargins(0, 0, 0, 0)
        subtitles_body_layout.setSpacing(6)

        self.speaker_table = QTableWidget()
        self.speaker_table.setColumnCount(4)
        self.speaker_table.setHorizontalHeaderLabels(["#", "Thời gian", "Nội dung", "Giọng nói"])
        self.speaker_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.speaker_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.speaker_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.speaker_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.speaker_table.verticalHeader().setVisible(False)
        subtitles_body_layout.addWidget(self.speaker_table)

        subtitles_card.set_body(subtitles_body)
        main_layout.addWidget(subtitles_card, 1)

        step3_card = _make_step_card(
            3,
            "Xuất âm thanh",
            "Tạo file âm thanh cuối cùng sau khi đã chọn giọng và rà soát nội dung.",
        )
        step3_body = QWidget(self)
        step3_layout = QVBoxLayout(step3_body)
        step3_layout.setContentsMargins(0, 0, 0, 0)
        step3_layout.setSpacing(10)
        button_layout = QHBoxLayout()

        self.generate_button = QPushButton("Tạo giọng nói")
        self.generate_button.setEnabled(False)
        self.generate_button.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: white; padding: 8px 14px; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1D4ED8; }"
            "QPushButton:disabled { background-color: #94A3B8; color: #E2E8F0; }"
        )
        self.generate_button.clicked.connect(self.generate_speech)
        button_layout.addWidget(self.generate_button)

        self.preview_button = QPushButton("Nghe thử")
        self.preview_button.setEnabled(False)
        self.preview_button.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #0F172A; padding: 8px 14px; border: 1px solid #CBD5E1; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background-color: #E2E8F0; }"
            "QPushButton:disabled { color: #94A3B8; border-color: #E2E8F0; }"
        )
        self.preview_button.clicked.connect(self.preview_speech)
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch(1)
        step3_layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        step3_layout.addWidget(self.progress_bar)

        step3_card.set_body(step3_body)
        main_layout.addWidget(step3_card)

    def load_voices(self):
        """Tải danh sách giọng nói theo nhà cung cấp TTS"""
        provider = self.tts_provider_combo.currentText() if hasattr(self, 'tts_provider_combo') else config.get("tts_provider", "ElevenLabs")

        if provider == "ElevenLabs":
            api_key = config.get("elevenlabs_api_key", "")
            if not api_key:
                QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
                return
            elevenlabs_api = ElevenLabsAPI(api_key=api_key)
            self.voices = elevenlabs_api.get_voices()
            if not self.voices:
                QMessageBox.warning(self, "Cảnh báo", "Không thể tải danh sách giọng nói từ ElevenLabs!")
                return
        elif provider == "Gemini":
            # Danh sách giọng nói Gemini là cố định, không cần API key
            gemini_tts = GeminiTTS(api_key=config.get("gemini_api_key", ""))
            self.voices = gemini_tts.get_voices() or []
            if not self.voices:
                QMessageBox.warning(self, "Cảnh báo", "Không thể tải danh sách giọng nói từ Gemini!")
                return
        else:
            edge_language = config.get("edge_tts_language", "")
            edge_model = EdgeTTSModel()
            self.voices = edge_model.list_voices(language_filter=edge_language) or []
            if not self.voices:
                QMessageBox.warning(self, "Cảnh báo", "Không thể tải danh sách giọng nói từ Edge TTS!")
                return

        # Sau khi load voices, cập nhật các bảng hiển thị
        self.update_speaker_mapping_table()
        self.update_speaker_table()

    def load_subtitle_file(self):
        """Tải file phụ đề hoặc file TXT"""
        from utils.file_dialog_utils import get_open_file_path

        file_path, _ = get_open_file_path(
            self,
            "Chọn file phụ đề hoặc file văn bản",
            "open_subtitle",
            "Subtitle and Text Files (*.srt *.txt);;Subtitle Files (*.srt);;Text Files (*.txt);;All Files (*.*)"
        )

        if not file_path:
            return

        # Kiểm tra loại file
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.srt':
            # Đọc file phụ đề SRT
            subtitles = SubtitleParser.load_srt(file_path)
            if not subtitles:
                QMessageBox.critical(self, "Lỗi", "Không thể đọc file phụ đề!")
                return
        elif file_ext == '.txt':
            # Đọc file TXT và tạo một đoạn phụ đề duy nhất
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read().strip()
                
                if not text_content:
                    QMessageBox.critical(self, "Lỗi", "File TXT trống!")
                    return
                
                # Tạo một đoạn phụ đề duy nhất từ nội dung TXT
                subtitles = [{
                    'index': 1,
                    'start': '00:00:00,000',
                    'end': '00:10:10,000',  # Mặc định 10 giây
                    'text': text_content,
                    'speaker': None
                }]
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đọc file TXT: {e}")
                return
        else:
            QMessageBox.critical(self, "Lỗi", "Chỉ hỗ trợ file SRT và TXT!")
            return

        # Lưu đường dẫn file
        self.subtitle_path = file_path
        self.subtitle_path_label.setText(file_path)

        # Tải phụ đề
        self.load_subtitles(subtitles, file_path)

    def load_subtitles(self, subtitles, subtitle_path=None):
        """
        Tải danh sách phụ đề

        Args:
            subtitles (list): Danh sách các đoạn phụ đề
            subtitle_path (str, optional): Đường dẫn file phụ đề. Mặc định là None.
        """
        self.subtitles = subtitles

        if subtitle_path:
            self.subtitle_path = subtitle_path
            self.subtitle_path_label.setText(subtitle_path)

        # Kiểm tra API key theo provider
        provider = self.tts_provider_combo.currentText() if hasattr(self, 'tts_provider_combo') else config.get("tts_provider", "ElevenLabs")
        if provider == "ElevenLabs":
            api_key = config.get("elevenlabs_api_key", "")
            if not api_key:
                QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
                return
        else:
            gemini_key = config.get("gemini_api_key", "")
            if not gemini_key:
                QMessageBox.warning(self, "Cảnh báo", "API key Gemini chưa được cấu hình!")
                return

        # Tải danh sách giọng nói nếu chưa có
        if not self.voices:
            self.load_voices()

        # Xác định danh sách người nói duy nhất
        self.speakers = set()
        for subtitle in subtitles:
            if subtitle.get('speaker'):
                self.speakers.add(subtitle['speaker'])

        # Cập nhật bảng người nói
        self.update_speaker_mapping_table()

        # Cập nhật bảng phụ đề
        self.update_speaker_table()

        # Bật nút tạo giọng nói
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        
        # Nếu là file TXT (chỉ có 1 đoạn), tự động chọn giọng nói mặc định
        if len(subtitles) == 1 and subtitle_path and subtitle_path.lower().endswith('.txt'):
            if self.voices:
                # Chọn giọng nói đầu tiên làm mặc định
                default_voice_id = self.voices[0].voice_id
                self.voice_selections[0] = default_voice_id
                # Cập nhật lại bảng để hiển thị giọng nói đã chọn
                self.update_speaker_table()

    def update_speaker_mapping_table(self):
        """Cập nhật bảng gán giọng nói cho người nói"""
        # Xóa tất cả các dòng
        self.speaker_mapping_table.setRowCount(0)

        # Thêm các dòng mới
        for speaker in sorted(self.speakers):
            row = self.speaker_mapping_table.rowCount()
            self.speaker_mapping_table.insertRow(row)

            # Người nói
            self.speaker_mapping_table.setItem(row, 0, QTableWidgetItem(speaker))

            # Giọng nói
            voice_combo = QComboBox()
            voice_combo.addItem("-- Chọn giọng nói --", "")

            # Thêm danh sách giọng nói
            for voice in self.voices:
                voice_combo.addItem(f"{voice.name}", voice.voice_id)

            # Đặt giọng nói mặc định nếu đã có trong speaker_voice_map
            if speaker in self.speaker_voice_map:
                voice_id = self.speaker_voice_map[speaker]
                for i in range(voice_combo.count()):
                    if voice_combo.itemData(i) == voice_id:
                        voice_combo.setCurrentIndex(i)
                        break
            # Nếu chưa có, tìm giọng nói phù hợp với tên người nói
            else:
                for i, voice in enumerate(self.voices):
                    if speaker.lower() in voice.name.lower():
                        voice_combo.setCurrentIndex(i + 1)  # +1 vì có item "-- Chọn giọng nói --"
                        self.speaker_voice_map[speaker] = voice.voice_id
                        break

            # Kết nối sự kiện thay đổi giọng nói
            voice_combo.currentIndexChanged.connect(lambda _idx, spk=speaker, combo=voice_combo: self.on_speaker_voice_changed(spk, combo))

            self.speaker_mapping_table.setCellWidget(row, 1, voice_combo)

    def on_speaker_voice_changed(self, speaker, combo):
        """Xử lý khi thay đổi giọng nói cho người nói"""
        voice_id = combo.currentData()
        if voice_id:
            self.speaker_voice_map[speaker] = voice_id

            # Tự động cập nhật giọng nói cho các đoạn phụ đề có cùng người nói
            for i, subtitle in enumerate(self.subtitles):
                if subtitle.get('speaker') and subtitle['speaker'] == speaker:
                    self.voice_selections[i] = voice_id

            # Cập nhật bảng phụ đề
            self.update_speaker_table()
        elif speaker in self.speaker_voice_map:
            del self.speaker_voice_map[speaker]

    def apply_speaker_voices(self):
        """\u00c1p d\u1ee5ng gi\u1ecdng n\u00f3i cho t\u1ea5t c\u1ea3 \u0111o\u1ea1n ph\u1ee5 \u0111\u1ec1 ch\u01b0a c\u00f3 gi\u1ecdng n\u00f3i"""
        if not self.subtitles:
            QMessageBox.warning(self, "Cảnh báo", "Không có phụ đề nào để gán giọng nói!")
            return

        # Kiểm tra xem có giọng nói nào chưa được gán không
        missing_voices = []
        for i, _ in enumerate(self.subtitles):
            if i not in self.voice_selections:
                missing_voices.append(i)

        if not missing_voices:
            QMessageBox.information(self, "Thông báo", "Tất cả các đoạn phụ đề đã có giọng nói!")
            return

        # Kiểm tra xem có giọng nói nào có sẵn không
        if not self.voices:
            QMessageBox.warning(self, "Cảnh báo", "Không có giọng nói nào có sẵn!")
            return

        # Hiển thị dialog chọn giọng nói
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Chọn giọng nói")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Thông báo
        message = QLabel(f"Chọn giọng nói để áp dụng cho {len(missing_voices)} đoạn phụ đề chưa có giọng nói:")
        layout.addWidget(message)

        # Combobox chọn giọng nói
        voice_combo = QComboBox()
        for voice in self.voices:
            voice_combo.addItem(f"{voice.name}", voice.voice_id)

        layout.addWidget(voice_combo)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Hiển thị dialog
        if dialog.exec_() == QDialog.Accepted:
            # Lấy giọng nói đã chọn
            selected_voice_id = voice_combo.currentData()
            selected_voice_name = voice_combo.currentText()

            if not selected_voice_id:
                return

            # Áp dụng giọng nói cho tất cả đoạn phụ đề chưa có giọng nói
            for i in missing_voices:
                self.voice_selections[i] = selected_voice_id

            # Cập nhật bảng phụ đề
            self.update_speaker_table()

            # Hiển thị thông báo
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã áp dụng giọng nói '{selected_voice_name}' cho {len(missing_voices)} đoạn phụ đề."
            )

    def update_speaker_table(self):
        """Cập nhật bảng cấu hình người nói"""
        # Xóa tất cả các dòng
        self.speaker_table.setRowCount(0)

        # Thêm các dòng mới
        for i, subtitle in enumerate(self.subtitles):
            row = self.speaker_table.rowCount()
            self.speaker_table.insertRow(row)

            # Số thứ tự
            item = QTableWidgetItem(str(i + 1))
            # Đánh dấu màu nếu đã có giọng nói được gán
            if i in self.voice_selections:
                item.setBackground(Qt.green)
            self.speaker_table.setItem(row, 0, item)

            # Thời gian (ẩn cho file TXT)
            if len(self.subtitles) == 1 and self.subtitle_path and self.subtitle_path.lower().endswith('.txt'):
                time_text = "Toàn bộ văn bản"
            else:
                time_text = f"{subtitle['start']} --> {subtitle['end']}"
            self.speaker_table.setItem(row, 1, QTableWidgetItem(time_text))

            # Nội dung và người nói
            text = subtitle['text']
            speaker_item = QTableWidgetItem(text)

            # Đánh dấu màu nếu có người nói và đã được gán giọng nói
            if subtitle.get('speaker'):
                speaker = subtitle['speaker']
                # Hiển thị người nói trong tooltip
                speaker_item.setToolTip(f"Người nói: {speaker}")

                # Đánh dấu màu nếu người nói đã được gán giọng nói
                if speaker in self.speaker_voice_map:
                    speaker_item.setBackground(Qt.lightGray)

            self.speaker_table.setItem(row, 2, speaker_item)

            # Giọng nói
            voice_combo = QComboBox()
            voice_combo.addItem("-- Chọn giọng nói --", "")

            # Thêm danh sách giọng nói
            for voice in self.voices:
                voice_combo.addItem(f"{voice.name}", voice.voice_id)

            # Đặt giọng nói nếu đã có trong voice_selections
            if i in self.voice_selections:
                voice_id = self.voice_selections[i]
                for j in range(voice_combo.count()):
                    if voice_combo.itemData(j) == voice_id:
                        voice_combo.setCurrentIndex(j)
                        break
            # Nếu chưa có nhưng có người nói và người nói đã được gán giọng nói
            elif subtitle.get('speaker') and subtitle['speaker'] in self.speaker_voice_map:
                voice_id = self.speaker_voice_map[subtitle['speaker']]
                for j in range(voice_combo.count()):
                    if voice_combo.itemData(j) == voice_id:
                        voice_combo.setCurrentIndex(j)
                        self.voice_selections[i] = voice_id
                        break

            # Kết nối sự kiện thay đổi giọng nói
            voice_combo.currentIndexChanged.connect(lambda _idx, row=i, combo=voice_combo: self.on_voice_changed(row, combo))

            self.speaker_table.setCellWidget(row, 3, voice_combo)

    def on_voice_changed(self, row, combo):
        """Xử lý khi thay đổi giọng nói cho đoạn phụ đề"""
        voice_id = combo.currentData()
        if voice_id:
            self.voice_selections[row] = voice_id

            # Nếu đoạn phụ đề có người nói, cập nhật giọng nói cho người nói đó
            subtitle = self.subtitles[row]
            if subtitle.get('speaker'):
                speaker = subtitle['speaker']
                # Cập nhật giọng nói cho người nói
                self.speaker_voice_map[speaker] = voice_id

                # Cập nhật bảng người nói
                self.update_speaker_mapping_table()
        elif row in self.voice_selections:
            del self.voice_selections[row]

    def preview_speech(self):
        """Nghe thử giọng nói"""
        # Kiểm tra xem có phụ đề nào được chọn không
        selected_items = self.speaker_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn một đoạn phụ đề để nghe thử!")
            return

        # Lấy dòng được chọn
        row = selected_items[0].row()

        provider = self.tts_provider_combo.currentText() if hasattr(self, 'tts_provider_combo') else "ElevenLabs"

        # Với ElevenLabs cần chọn voice theo đoạn
        if provider == "ElevenLabs" and row not in self.voice_selections:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn giọng nói cho đoạn phụ đề này!")
            return

        # Lấy thông tin phụ đề và giọng nói
        subtitle = self.subtitles[row]
        voice_id = self.voice_selections.get(row)
        
        # Với file TXT, giới hạn text nghe thử không quá 80 ký tự
        text_to_speak = subtitle['text']
        if len(self.subtitles) == 1 and self.subtitle_path and self.subtitle_path.lower().endswith('.txt'):
            if len(text_to_speak) > 80:
                text_to_speak = text_to_speak[:80] + "..."

        # Tạo file tạm
        temp_dir = config.temp_dir
        temp_dir.mkdir(exist_ok=True)
        # Đặt đuôi file nghe thử theo provider
        temp_ext = ".mp3"
        temp_file = temp_dir / f"preview_{int(time.time())}{temp_ext}"

        # Tạo giọng nói theo provider
        if provider == "ElevenLabs":
            api_key = config.get("elevenlabs_api_key", "")
            elevenlabs_api = ElevenLabsAPI(api_key=api_key)
        elif provider == "Gemini":
            gemini_key = config.get("gemini_api_key", "")
            gemini_tts = GeminiTTS(api_key=gemini_key)
        else:
            edge_model = EdgeTTSModel()

        # Hiển thị thanh tiến trình
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        QApplication.processEvents()

        # Tạo giọng nói
        if provider == "ElevenLabs":
            result = elevenlabs_api.text_to_speech_with_retry(
                text=text_to_speak,
                voice_id=voice_id,
                output_path=str(temp_file)
            )
        elif provider == "Gemini":
            result = gemini_tts.text_to_speech_with_retry(
                text=text_to_speak,
                output_path=str(temp_file),
                voice_name=voice_id if voice_id else None,
                audio_format="MP3"
            )
        else:
            result = edge_model.synthesize(
                text=text_to_speak,
                voice=voice_id or "vi-VN-NamMinhNeural",
                output_path=str(temp_file)
            )

        # Ẩn thanh tiến trình
        self.progress_bar.setVisible(False)

        if not result:
            QMessageBox.critical(self, "Lỗi", "Không thể tạo giọng nói!")
            return

        # Phát file âm thanh
        try:
            import os
            os.startfile(str(temp_file))
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể phát file âm thanh: {e}")

    def generate_speech(self):
        """Tạo giọng nói cho tất cả các đoạn phụ đề"""
        # Kiểm tra xem có phụ đề nào không
        if not self.subtitles:
            QMessageBox.warning(self, "Cảnh báo", "Không có phụ đề nào để tạo giọng nói!")
            return

        # Kiểm tra xem có giọng nói nào được chọn không
        if not self.voice_selections:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn giọng nói cho ít nhất một đoạn phụ đề!")
            return

        # Kiểm tra xem tất cả các đoạn phụ đề đã có giọng nói chưa
        missing_voices = []
        for i, _subtitle in enumerate(self.subtitles):
            if i not in self.voice_selections:
                missing_voices.append(i + 1)

        # Nếu là file TXT (chỉ có 1 đoạn) và chưa có giọng nói, yêu cầu chọn
        if len(self.subtitles) == 1 and self.subtitle_path and self.subtitle_path.lower().endswith('.txt'):
            if 0 not in self.voice_selections:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn giọng nói cho file văn bản!")
                return
        elif missing_voices:
            reply = QMessageBox.question(
                self,
                "Cảnh báo",
                f"Các đoạn phụ đề sau chưa có giọng nói: {', '.join(map(str, missing_voices))}.\n"
                f"Bạn có muốn tiếp tục không?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        # Chọn file đầu ra
        from utils.file_dialog_utils import get_save_file_path

        output_path, _ = get_save_file_path(
            self,
            "Lưu file âm thanh",
            "save_audio",
            "Audio Files (*.wav)",
            default_suffix=".wav"
        )

        if not output_path:
            return

        # Vô hiệu hóa các nút
        self.generate_button.setEnabled(False)
        self.preview_button.setEnabled(False)

        # Hiển thị thanh tiến trình
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        # Lấy tùy chọn lưu file âm thanh gốc
        save_original = config.get("save_original_audio", True)

        # Hiển thị dialog tùy chọn
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Tùy chọn tạo giọng nói")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Tùy chọn lưu file âm thanh gốc
        save_original_checkbox = QCheckBox("Lưu file âm thanh gốc từ ElevenLabs")
        save_original_checkbox.setChecked(save_original)
        layout.addWidget(save_original_checkbox)

        # Thêm thông tin về vị trí lưu
        info_label = QLabel(f"File âm thanh gốc sẽ được lưu trong thư mục:\n{config.output_dir / os.path.splitext(os.path.basename(output_path))[0]}")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Nút OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Hiển thị dialog
        if dialog.exec_() == QDialog.Accepted:
            # Lưu cài đặt
            save_original = save_original_checkbox.isChecked()
            config.set("save_original_audio", save_original)

            # Tạo worker thread
            self.speech_worker = SpeechGenerationWorker(
                self.subtitles,
                self.voice_selections,
                output_path,
                save_original=save_original,
                tts_provider=self.tts_provider_combo.currentText() if hasattr(self, 'tts_provider_combo') else "ElevenLabs",
                subtitle_path=self.subtitle_path
            )
        else:
            return

        # Kết nối tín hiệu
        self.speech_worker.progress.connect(self.update_progress)
        self.speech_worker.segment_finished.connect(self.on_segment_finished)
        self.speech_worker.finished.connect(self.on_speech_generation_finished)
        self.speech_worker.error.connect(self.on_speech_generation_error)

        # Bắt đầu worker thread
        self.speech_worker.start()

    def update_progress(self, value):
        """Cập nhật thanh tiến trình"""
        self.progress_bar.setValue(value)

    def add_speaker(self):
        """Thêm người nói mới"""
        # Hiển thị dialog thêm người nói
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Thêm người nói mới")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)

        # Form nhập thông tin
        form_layout = QFormLayout()

        # Tên người nói
        name_input = QLineEdit()
        form_layout.addRow("Tên người nói:", name_input)

        layout.addLayout(form_layout)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Hiển thị dialog
        if dialog.exec_() == QDialog.Accepted:
            # Lấy thông tin
            speaker_name = name_input.text().strip()

            # Kiểm tra thông tin
            if not speaker_name:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập tên người nói!")
                return

            # Kiểm tra xem người nói đã tồn tại chưa
            if speaker_name in self.speakers:
                QMessageBox.warning(self, "Cảnh báo", f"Người nói '{speaker_name}' đã tồn tại!")
                return

            # Thêm người nói mới
            self.speakers.add(speaker_name)

            # Cập nhật bảng người nói
            self.update_speaker_mapping_table()

            # Hiển thị thông báo
            QMessageBox.information(self, "Thành công", f"Đã thêm người nói: {speaker_name}")

    def edit_speaker(self):
        """Sửa tên người nói"""
        # Kiểm tra danh sách người nói
        if not self.speakers:
            QMessageBox.warning(self, "Cảnh báo", "Không có người nói nào để sửa!")
            return

        # Hiển thị dialog chọn người nói
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QVBoxLayout

        # Dialog chọn người nói
        select_dialog = QDialog(self)
        select_dialog.setWindowTitle("Chọn người nói")
        select_dialog.setMinimumWidth(300)

        select_layout = QVBoxLayout(select_dialog)

        # Danh sách người nói
        speaker_combo = QComboBox()
        for speaker in sorted(self.speakers):
            speaker_combo.addItem(speaker)

        select_layout.addWidget(QLabel("Chọn người nói cần sửa:"))
        select_layout.addWidget(speaker_combo)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(select_dialog.accept)
        button_box.rejected.connect(select_dialog.reject)
        select_layout.addWidget(button_box)

        # Hiển thị dialog chọn người nói
        if select_dialog.exec_() != QDialog.Accepted:
            return

        # Lấy người nói đã chọn
        old_speaker = speaker_combo.currentText()

        # Hiển thị dialog sửa người nói
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle(f"Sửa người nói: {old_speaker}")
        edit_dialog.setMinimumWidth(300)

        edit_layout = QVBoxLayout(edit_dialog)

        # Form nhập thông tin
        form_layout = QFormLayout()

        # Tên người nói
        name_input = QLineEdit(old_speaker)
        form_layout.addRow("Tên người nói mới:", name_input)

        edit_layout.addLayout(form_layout)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(edit_dialog.accept)
        button_box.rejected.connect(edit_dialog.reject)
        edit_layout.addWidget(button_box)

        # Hiển thị dialog sửa người nói
        if edit_dialog.exec_() == QDialog.Accepted:
            # Lấy thông tin
            new_speaker = name_input.text().strip()

            # Kiểm tra thông tin
            if not new_speaker:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập tên người nói!")
                return

            # Kiểm tra xem tên mới đã tồn tại chưa (trừ tên cũ)
            if new_speaker != old_speaker and new_speaker in self.speakers:
                QMessageBox.warning(self, "Cảnh báo", f"Người nói '{new_speaker}' đã tồn tại!")
                return

            # Cập nhật tên người nói trong danh sách người nói
            self.speakers.remove(old_speaker)
            self.speakers.add(new_speaker)

            # Cập nhật tên người nói trong danh sách phụ đề
            for subtitle in self.subtitles:
                if subtitle.get('speaker') == old_speaker:
                    subtitle['speaker'] = new_speaker

            # Cập nhật giọng nói cho người nói mới
            if old_speaker in self.speaker_voice_map:
                voice_id = self.speaker_voice_map[old_speaker]
                self.speaker_voice_map[new_speaker] = voice_id
                del self.speaker_voice_map[old_speaker]

            # Cập nhật bảng người nói và phụ đề
            self.update_speaker_mapping_table()
            self.update_speaker_table()

            # Hiển thị thông báo
            QMessageBox.information(self, "Thành công", f"Đã sửa người nói: {old_speaker} -> {new_speaker}")

    def on_segment_finished(self, index, _file_path):
        """Xử lý khi một đoạn phụ đề đã được tạo giọng nói"""
        # Đánh dấu đoạn phụ đề đã hoàn thành
        item = self.speaker_table.item(index, 0)
        if item:
            item.setBackground(Qt.green)

    def refresh_voices(self):
        """Làm mới danh sách giọng nói"""
        provider = self.tts_provider_combo.currentText() if hasattr(self, 'tts_provider_combo') else config.get("tts_provider", "ElevenLabs")
        if provider == "ElevenLabs":
            api_key = config.get("elevenlabs_api_key", "")
            if not api_key:
                QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
                return
            elevenlabs_api = ElevenLabsAPI(api_key=api_key)
            self.voices = elevenlabs_api.get_voices(force_refresh=True)
            if not self.voices:
                QMessageBox.warning(self, "Cảnh báo", "Không thể tải danh sách giọng nói từ ElevenLabs!")
                return
            QMessageBox.information(self, "Thành công", f"Đã tải {len(self.voices)} giọng nói từ ElevenLabs!")
        elif provider == "Gemini":
            # Danh sách giọng nói Gemini là cố định, không cần API key
            gemini_tts = GeminiTTS(api_key=config.get("gemini_api_key", ""))
            self.voices = gemini_tts.get_voices() or []
            if not self.voices:
                QMessageBox.warning(self, "Cảnh báo", "Không thể tải danh sách giọng nói từ Gemini!")
                return
            QMessageBox.information(self, "Thành công", f"Đã tải {len(self.voices)} giọng nói từ Gemini!")
        else:
            # Edge TTS
            edge_language = config.get("edge_tts_language", "")
            edge_model = EdgeTTSModel()
            self.voices = edge_model.list_voices(language_filter=edge_language) or []
            if not self.voices:
                QMessageBox.warning(self, "Cảnh báo", "Không thể tải danh sách giọng nói từ Edge TTS!")
                return
            QMessageBox.information(self, "Thành công", f"Đã tải {len(self.voices)} giọng nói từ Edge TTS!")

        # Cập nhật bảng người nói và phụ đề
        self.update_speaker_mapping_table()
        self.update_speaker_table()

    def add_voice(self):
        """Thêm giọng nói mới hoặc thêm giọng nói từ ID"""
        # Kiểm tra API key
        api_key = config.get("elevenlabs_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
            return

        # Hiển thị dialog chọn phương thức thêm giọng nói
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QRadioButton, QButtonGroup

        method_dialog = QDialog(self)
        method_dialog.setWindowTitle("Thêm giọng nói")
        method_dialog.setMinimumWidth(300)

        method_layout = QVBoxLayout(method_dialog)
        method_layout.addWidget(QLabel("Chọn phương thức thêm giọng nói:"))

        # Tạo các radio button cho phương thức
        create_new_radio = QRadioButton("Tạo giọng nói mới từ file âm thanh")
        create_new_radio.setChecked(True)
        add_existing_radio = QRadioButton("Thêm giọng nói từ ID ElevenLabs")

        method_layout.addWidget(create_new_radio)
        method_layout.addWidget(add_existing_radio)

        # Nhóm các radio button
        method_group = QButtonGroup(method_dialog)
        method_group.addButton(create_new_radio, 1)
        method_group.addButton(add_existing_radio, 2)

        # Nút xác nhận
        method_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        method_button_box.accepted.connect(method_dialog.accept)
        method_button_box.rejected.connect(method_dialog.reject)
        method_layout.addWidget(method_button_box)

        # Hiển thị dialog chọn phương thức
        if method_dialog.exec_() != QDialog.Accepted:
            return

        # Xác định phương thức đã chọn
        selected_method = method_group.checkedId()

        if selected_method == 1:
            # Tạo giọng nói mới từ file âm thanh
            self.create_new_voice()
        elif selected_method == 2:
            # Thêm giọng nói từ ID ElevenLabs
            self.add_voice_by_id()

    def create_new_voice(self):
        """Tạo giọng nói mới từ file âm thanh"""
        # Kiểm tra API key
        api_key = config.get("elevenlabs_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
            return

        # Hiển thị dialog thêm giọng nói
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Tạo giọng nói mới")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Form nhập thông tin
        form_layout = QFormLayout()

        # Tên giọng nói
        name_input = QLineEdit()
        form_layout.addRow("Tên giọng nói:", name_input)

        # Mô tả
        description_input = QTextEdit()
        description_input.setMaximumHeight(100)
        form_layout.addRow("Mô tả:", description_input)

        # File âm thanh mẫu
        audio_files_label = QLabel("Chưa có file âm thanh nào được chọn")
        audio_files_button = QPushButton("Chọn file âm thanh")
        audio_files_layout = QHBoxLayout()
        audio_files_layout.addWidget(audio_files_label, 1)
        audio_files_layout.addWidget(audio_files_button)
        form_layout.addRow("File âm thanh mẫu:", audio_files_layout)

        # Danh sách file âm thanh
        audio_files = []

        # Xử lý khi chọn file âm thanh
        def select_audio_files():
            from utils.file_dialog_utils import get_open_file_paths

            file_paths, _ = get_open_file_paths(
                dialog,
                "Chọn file âm thanh mẫu",
                "open_audio",
                "Audio Files (*.mp3 *.wav *.m4a *.flac)"
            )

            if file_paths:
                audio_files.clear()
                audio_files.extend(file_paths)
                audio_files_label.setText(f"Đã chọn {len(file_paths)} file âm thanh")

        audio_files_button.clicked.connect(select_audio_files)

        layout.addLayout(form_layout)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Hiển thị dialog
        if dialog.exec_() != QDialog.Accepted:
            return

        # Lấy thông tin
        name = name_input.text().strip()
        description = description_input.toPlainText().strip()

        # Kiểm tra thông tin
        if not name:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập tên giọng nói!")
            return

        if not audio_files:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một file âm thanh mẫu!")
            return

        # Hiển thị thanh tiến trình
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        # Tạo giọng nói mới
        elevenlabs_api = ElevenLabsAPI(api_key=api_key)

        # Cập nhật tiến trình
        self.progress_bar.setValue(30)

        # Tạo giọng nói
        result = elevenlabs_api.create_voice(name, description, audio_files)

        # Ẩn thanh tiến trình
        self.progress_bar.setVisible(False)

        if result:
            # Làm mới danh sách giọng nói
            self.voices = elevenlabs_api.get_voices(force_refresh=True)

            # Cập nhật bảng người nói và phụ đề
            self.update_speaker_mapping_table()
            self.update_speaker_table()

            # Hiển thị thông báo
            voice_id = result.get("voice_id", "")
            QMessageBox.information(self, "Thành công", f"Đã tạo giọng nói mới: {name}\nID: {voice_id}")
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể tạo giọng nói mới!")

    def add_voice_by_id(self):
        """Thêm giọng nói từ ID ElevenLabs"""
        # Kiểm tra API key
        api_key = config.get("elevenlabs_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
            return

        # Hiển thị dialog nhập ID giọng nói
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Thêm giọng nói từ ID")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Form nhập thông tin
        form_layout = QFormLayout()

        # Tên giọng nói
        name_input = QLineEdit()
        form_layout.addRow("Tên hiển thị:", name_input)

        # ID giọng nói
        voice_id_input = QLineEdit()
        form_layout.addRow("ID giọng nói ElevenLabs:", voice_id_input)

        layout.addLayout(form_layout)

        # Thêm hướng dẫn
        help_text = QLabel("Lưu ý: ID giọng nói có thể lấy từ trang web ElevenLabs hoặc từ API của ElevenLabs.")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Hiển thị dialog
        if dialog.exec_() != QDialog.Accepted:
            return

        # Lấy thông tin đã nhập
        name = name_input.text().strip()
        voice_id = voice_id_input.text().strip()

        # Kiểm tra thông tin
        if not name:
            QMessageBox.warning(self, "Cảnh báo", "Tên hiển thị không được để trống!")
            return

        if not voice_id:
            QMessageBox.warning(self, "Cảnh báo", "ID giọng nói không được để trống!")
            return

        # Kiểm tra xem ID giọng nói đã tồn tại trong danh sách chưa
        for voice in self.voices:
            if voice.voice_id == voice_id:
                QMessageBox.warning(self, "Cảnh báo", f"Giọng nói với ID '{voice_id}' đã tồn tại trong danh sách!")
                return

        # Hiển thị thanh tiến trình
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        try:
            # Tạo đối tượng ElevenLabsAPI
            elevenlabs_api = ElevenLabsAPI(api_key=api_key)

            # Cập nhật tiến trình
            self.progress_bar.setValue(50)

            # Làm mới danh sách giọng nói
            voices = elevenlabs_api.get_voices(force_refresh=True)

            # Kiểm tra xem ID giọng nói có hợp lệ không
            voice_found = False
            for voice in voices:
                if voice.voice_id == voice_id:
                    voice_found = True
                    break

            # Ẩn thanh tiến trình
            self.progress_bar.setVisible(False)

            if voice_found:
                # Cập nhật danh sách giọng nói
                self.voices = voices

                # Cập nhật bảng người nói và phụ đề
                self.update_speaker_mapping_table()
                self.update_speaker_table()

                # Hiển thị thông báo
                QMessageBox.information(self, "Thành công", f"Đã thêm giọng nói: {name}\nID: {voice_id}")
            else:
                QMessageBox.warning(self, "Cảnh báo", f"Không tìm thấy giọng nói với ID '{voice_id}' trong tài khoản ElevenLabs của bạn!")
        except Exception as e:
            # Ẩn thanh tiến trình
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm giọng nói: {str(e)}")

    def edit_voice(self):
        """Sửa giọng nói"""
        # Kiểm tra API key
        api_key = config.get("elevenlabs_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
            return

        # Kiểm tra danh sách giọng nói
        if not self.voices:
            QMessageBox.warning(self, "Cảnh báo", "Không có giọng nói nào để sửa!")
            return

        # Hiển thị dialog chọn giọng nói
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QVBoxLayout

        # Dialog chọn giọng nói
        select_dialog = QDialog(self)
        select_dialog.setWindowTitle("Chọn giọng nói")
        select_dialog.setMinimumWidth(300)

        select_layout = QVBoxLayout(select_dialog)

        # Danh sách giọng nói
        voice_combo = QComboBox()
        for voice in self.voices:
            voice_combo.addItem(f"{voice.name}", voice.voice_id)

        select_layout.addWidget(QLabel("Chọn giọng nói cần sửa:"))
        select_layout.addWidget(voice_combo)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(select_dialog.accept)
        button_box.rejected.connect(select_dialog.reject)
        select_layout.addWidget(button_box)

        # Hiển thị dialog chọn giọng nói
        if select_dialog.exec_() != QDialog.Accepted:
            return

        # Lấy giọng nói đã chọn
        voice_id = voice_combo.currentData()
        selected_voice = None

        for voice in self.voices:
            if voice.voice_id == voice_id:
                selected_voice = voice
                break

        if not selected_voice:
            QMessageBox.critical(self, "Lỗi", "Không tìm thấy giọng nói đã chọn!")
            return

        # Hiển thị dialog sửa giọng nói
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle(f"Sửa giọng nói: {selected_voice.name}")
        edit_dialog.setMinimumWidth(400)

        edit_layout = QVBoxLayout(edit_dialog)

        # Form nhập thông tin
        form_layout = QFormLayout()

        # Tên giọng nói
        name_input = QLineEdit(selected_voice.name)
        form_layout.addRow("Tên giọng nói:", name_input)

        # Mô tả
        description_input = QTextEdit(selected_voice.description)
        description_input.setMaximumHeight(100)
        form_layout.addRow("Mô tả:", description_input)

        edit_layout.addLayout(form_layout)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(edit_dialog.accept)
        button_box.rejected.connect(edit_dialog.reject)
        edit_layout.addWidget(button_box)

        # Hiển thị dialog sửa giọng nói
        if edit_dialog.exec_() == QDialog.Accepted:
            # Lấy thông tin
            name = name_input.text().strip()
            description = description_input.toPlainText().strip()

            # Kiểm tra thông tin
            if not name:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập tên giọng nói!")
                return

            # Hiển thị thanh tiến trình
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)

            # Sửa giọng nói
            elevenlabs_api = ElevenLabsAPI(api_key=api_key)

            # Cập nhật tiến trình
            self.progress_bar.setValue(30)

            # Sửa giọng nói
            success = elevenlabs_api.edit_voice(voice_id, name, description)

            # Ẩn thanh tiến trình
            self.progress_bar.setVisible(False)

            if success:
                # Làm mới danh sách giọng nói
                self.voices = elevenlabs_api.get_voices(force_refresh=True)

                # Cập nhật bảng người nói và phụ đề
                self.update_speaker_mapping_table()
                self.update_speaker_table()

                # Hiển thị thông báo
                QMessageBox.information(self, "Thành công", f"Đã sửa giọng nói: {name}")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể sửa giọng nói!")

    def delete_voice(self):
        """Xóa giọng nói"""
        # Kiểm tra API key
        api_key = config.get("elevenlabs_api_key", "")
        if not api_key:
            QMessageBox.warning(self, "Cảnh báo", "API key ElevenLabs chưa được cấu hình!")
            return

        # Kiểm tra danh sách giọng nói
        if not self.voices:
            QMessageBox.warning(self, "Cảnh báo", "Không có giọng nói nào để xóa!")
            return

        # Hiển thị dialog chọn giọng nói
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox

        # Dialog chọn giọng nói
        select_dialog = QDialog(self)
        select_dialog.setWindowTitle("Chọn giọng nói")
        select_dialog.setMinimumWidth(300)

        select_layout = QVBoxLayout(select_dialog)

        # Danh sách giọng nói
        voice_combo = QComboBox()
        for voice in self.voices:
            voice_combo.addItem(f"{voice.name}", voice.voice_id)

        select_layout.addWidget(QLabel("Chọn giọng nói cần xóa:"))
        select_layout.addWidget(voice_combo)

        # Nút xác nhận
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(select_dialog.accept)
        button_box.rejected.connect(select_dialog.reject)
        select_layout.addWidget(button_box)

        # Hiển thị dialog chọn giọng nói
        if select_dialog.exec_() != QDialog.Accepted:
            return

        # Lấy giọng nói đã chọn
        voice_id = voice_combo.currentData()
        voice_name = voice_combo.currentText()

        # Xác nhận xóa
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            f"Bạn có chắc chắn muốn xóa giọng nói: {voice_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Hiển thị thanh tiến trình
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        # Xóa giọng nói
        elevenlabs_api = ElevenLabsAPI(api_key=api_key)

        # Cập nhật tiến trình
        self.progress_bar.setValue(30)

        # Xóa giọng nói
        success = elevenlabs_api.delete_voice(voice_id)

        # Ẩn thanh tiến trình
        self.progress_bar.setVisible(False)

        if success:
            # Làm mới danh sách giọng nói
            self.voices = elevenlabs_api.get_voices(force_refresh=True)

            # Cập nhật bảng người nói và phụ đề
            self.update_speaker_mapping_table()
            self.update_speaker_table()

            # Hiển thị thông báo
            QMessageBox.information(self, "Thành công", f"Đã xóa giọng nói: {voice_name}")
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể xóa giọng nói!")

    def on_speech_generation_finished(self, output_path):
        """Xử lý khi tạo giọng nói hoàn tất"""
        # Bật lại các nút
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)

        # Ẩn thanh tiến trình
        self.progress_bar.setVisible(False)

        # Hiển thị thông báo
        QMessageBox.information(
            self,
            "Hoàn tất",
            f"Đã tạo giọng nói thành công!\n"
            f"File âm thanh: {output_path}"
        )

        # Phát file âm thanh
        try:
            import os
            os.startfile(output_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể phát file âm thanh: {e}")

    def on_speech_generation_error(self, error_message):
        """Xử lý khi có lỗi trong quá trình tạo giọng nói"""
        # Bật lại các nút
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)

        # Ẩn thanh tiến trình
        self.progress_bar.setVisible(False)

        # Hiển thị thông báo lỗi
        QMessageBox.critical(self, "Lỗi", f"Lỗi khi tạo giọng nói: {error_message}")
