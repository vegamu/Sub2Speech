from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sub2speech.core.speaker_assignment import check_overlap, parse_segment_ranges
from sub2speech.models.speaker import Speaker
from sub2speech.utils.logging_utils import log_info


class SpeakerManager(QWidget):
    speakers_changed = Signal()
    preview_voice_requested = Signal(str, str, str, str, str)

    def __init__(self) -> None:
        super().__init__()
        self.speakers: dict[str, Speaker] = {}
        self.max_index = 0
        self.voice_groups = {}
        self.txt_mode = False

        self.name_input = QLineEdit()
        self.range_input = QLineEdit()
        self.language_combo = QComboBox()
        self.voice_combo = QComboBox()
        self.rate_input = QLineEdit("+0%")
        self.volume_input = QLineEdit("+0%")
        self.pitch_input = QLineEdit("+0Hz")
        self.mode_hint = QLabel("")
        self.name_label = QLabel("Tên người nói")
        self.range_label = QLabel("Danh sách đoạn")
        self.language_label = QLabel("Ngôn ngữ")
        self.voice_label = QLabel("Giọng đọc")
        self.rate_label = QLabel("Tốc độ")
        self.volume_label = QLabel("Âm lượng")
        self.pitch_label = QLabel("Cao độ")
        self.voice_options_label = QLabel("Tùy chỉnh giọng")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Người nói", "Các đoạn", "Ngôn ngữ", "Giọng"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._load_selected_to_form)

        self.add_btn = QPushButton("Thêm/Cập nhật")
        self.remove_btn = QPushButton("Xóa")
        self.preview_btn = QPushButton("Nghe thử giọng")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.upsert_speaker)
        self.remove_btn.clicked.connect(self.delete_selected)
        self.preview_btn.clicked.connect(self.preview_voice)
        self.language_combo.currentTextChanged.connect(self._populate_voices)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_params_changed)
        self.rate_input.editingFinished.connect(self._on_voice_params_changed)
        self.volume_input.editingFinished.connect(self._on_voice_params_changed)
        self.pitch_input.editingFinished.connect(self._on_voice_params_changed)

        self.voice_section_title = QLabel("Thiết lập giọng")
        self.voice_section_title.setObjectName("sectionTitle")
        self.mapping_section_title = QLabel("Gán người nói")
        self.mapping_section_title.setObjectName("sectionTitle")
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setStyleSheet("color: #e2e8f0;")

        options_row = QHBoxLayout()
        options_row.setContentsMargins(0, 0, 0, 0)
        options_row.setSpacing(6)
        options_row.addWidget(self.rate_label)
        options_row.addWidget(self.rate_input)
        options_row.addWidget(self.volume_label)
        options_row.addWidget(self.volume_input)
        options_row.addWidget(self.pitch_label)
        options_row.addWidget(self.pitch_input)
        self.voice_options_widget = QWidget()
        self.voice_options_widget.setLayout(options_row)

        self.top_form = QFormLayout()
        self.top_form.setContentsMargins(0, 0, 0, 0)
        self.top_form.setSpacing(6)
        self.top_form.addRow(self.name_label, self.name_input)
        self.top_form.addRow(self.range_label, self.range_input)
        self.top_form.addRow(self.language_label, self.language_combo)
        self.top_form.addRow(self.voice_label, self.voice_combo)
        self.top_form.addRow(self.voice_options_label, self.voice_options_widget)
        self.top_form.addRow("", self.mode_hint)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.preview_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.voice_section_title)
        layout.addLayout(self.top_form)
        layout.addWidget(self.separator)
        layout.addWidget(self.mapping_section_title)
        layout.addLayout(btn_layout)
        layout.addWidget(self.table, 1)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.voice_options_widget.setMaximumHeight(34)
        self.mode_hint.setWordWrap(True)

    def set_max_index(self, max_index: int) -> None:
        self.max_index = max_index

    def set_voice_groups(self, grouped: dict, preferred_group: str = "") -> None:
        self.voice_groups = grouped
        self.language_combo.clear()
        self.voice_combo.clear()
        for group in grouped:
            self.language_combo.addItem(group)
        if preferred_group:
            idx = self.language_combo.findText(preferred_group)
            if idx >= 0:
                self.language_combo.setCurrentIndex(idx)
        self._populate_voices()

    def current_language_group(self) -> str:
        return self.language_combo.currentText()

    def set_txt_mode(self, enabled: bool) -> None:
        self.txt_mode = enabled
        self._set_field_collapsed(self.name_label, self.name_input, enabled)
        self._set_field_collapsed(self.range_label, self.range_input, enabled)
        self.add_btn.setVisible(not enabled)
        self.remove_btn.setVisible(not enabled)
        self.mapping_section_title.setVisible(not enabled)
        self.separator.setVisible(not enabled)
        self.table.setVisible(not enabled)
        self.mode_hint.setText(
            "Chế độ TXT: chỉ cần chọn giọng và tham số, áp dụng cho toàn bộ đoạn."
            if enabled
            else ""
        )
        if enabled:
            self._apply_txt_voice_settings()

    def _set_field_collapsed(self, label_widget: QLabel, field_widget: QWidget, collapsed: bool) -> None:
        if collapsed:
            label_widget.setVisible(False)
            field_widget.setVisible(False)
            label_widget.setMaximumHeight(0)
            field_widget.setMaximumHeight(0)
            label_widget.setMinimumHeight(0)
            field_widget.setMinimumHeight(0)
        else:
            label_widget.setVisible(True)
            field_widget.setVisible(True)
            label_widget.setMinimumHeight(0)
            field_widget.setMinimumHeight(0)
            label_widget.setMaximumHeight(16777215)
            field_widget.setMaximumHeight(16777215)

    def apply_txt_voice_settings(self) -> None:
        self._apply_txt_voice_settings()

    def preview_voice(self) -> None:
        voice = self.voice_combo.currentData()
        if not voice:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn giọng đọc để nghe thử")
            return
        self.preview_voice_requested.emit(
            "Xin chào, đây là giọng đọc mẫu.",
            str(voice),
            self._normalize_rate(self.rate_input.text()),
            self._normalize_volume(self.volume_input.text()),
            self._normalize_pitch(self.pitch_input.text()),
        )

    def upsert_speaker(self) -> None:
        if self.txt_mode:
            self._apply_txt_voice_settings()
            return
        name = self.name_input.text().strip()
        ranges = self.range_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Cảnh báo", "Tên người nói không được để trống")
            return
        try:
            segments = parse_segment_ranges(ranges, self.max_index)
        except ValueError as exc:
            QMessageBox.warning(self, "Cảnh báo", str(exc))
            return

        speaker = self.speakers.get(name, Speaker(name=name))
        speaker.segments = segments
        speaker.voice = self.voice_combo.currentData() or ""
        speaker.language_group = self.language_combo.currentText()
        speaker.rate = self._normalize_rate(self.rate_input.text())
        speaker.volume = self._normalize_volume(self.volume_input.text())
        speaker.pitch = self._normalize_pitch(self.pitch_input.text())
        if not speaker.voice:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn giọng đọc")
            return
        self.speakers[name] = speaker
        log_info(
            f"Upsert speaker name={name} segments={sorted(segments)} voice={speaker.voice} rate={speaker.rate} volume={speaker.volume} pitch={speaker.pitch}"
        )
        self.refresh()

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        self.speakers.pop(name_item.text(), None)
        log_info(f"Deleted speaker name={name_item.text()}")
        self.refresh()

    def refresh(self) -> None:
        overlaps = check_overlap({name: sp.segments for name, sp in self.speakers.items()})
        if overlaps:
            QMessageBox.warning(
                self,
                "Cảnh báo trùng đoạn",
                f"Đoạn bị gán nhiều người nói: {', '.join(str(i) for i in sorted(overlaps))}",
            )

        self.table.setRowCount(0)
        for speaker in self.speakers.values():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(speaker.name))
            self.table.setItem(row, 1, QTableWidgetItem(_compress_ranges(speaker.segments)))
            self.table.setItem(row, 2, QTableWidgetItem(speaker.language_group))
            self.table.setItem(row, 3, QTableWidgetItem(speaker.voice))
        self.speakers_changed.emit()

    def _populate_voices(self) -> None:
        language = self.language_combo.currentText()
        current_voice = self.voice_combo.currentData()
        self.voice_combo.clear()
        for voice in self.voice_groups.get(language, []):
            self.voice_combo.addItem(f"{voice.display_name} ({voice.gender})", voice.short_name)
        if current_voice:
            idx = self.voice_combo.findData(current_voice)
            if idx >= 0:
                self.voice_combo.setCurrentIndex(idx)

    def _load_selected_to_form(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        speaker = self.speakers.get(name_item.text())
        if not speaker:
            return
        self.name_input.setText(speaker.name)
        self.range_input.setText(_compress_ranges(speaker.segments))
        if speaker.language_group:
            lang_idx = self.language_combo.findText(speaker.language_group)
            if lang_idx >= 0:
                self.language_combo.setCurrentIndex(lang_idx)
        if speaker.voice:
            voice_idx = self.voice_combo.findData(speaker.voice)
            if voice_idx >= 0:
                self.voice_combo.setCurrentIndex(voice_idx)
        self.rate_input.setText(speaker.rate or "+0%")
        self.volume_input.setText(speaker.volume or "+0%")
        self.pitch_input.setText(speaker.pitch or "+0Hz")

    def _normalize_rate(self, value: str) -> str:
        text = (value or "").strip()
        return text if text else "+0%"

    def _normalize_volume(self, value: str) -> str:
        text = (value or "").strip()
        return text if text else "+0%"

    def _normalize_pitch(self, value: str) -> str:
        text = (value or "").strip()
        return text if text else "+0Hz"

    def _on_voice_params_changed(self) -> None:
        if self.txt_mode:
            self._apply_txt_voice_settings()

    def _apply_txt_voice_settings(self) -> None:
        voice = self.voice_combo.currentData() or ""
        if not voice:
            return
        speaker = self.speakers.get("TXT", Speaker(name="TXT"))
        speaker.segments = set(range(1, self.max_index + 1))
        speaker.voice = voice
        speaker.language_group = self.language_combo.currentText()
        speaker.rate = self._normalize_rate(self.rate_input.text())
        speaker.volume = self._normalize_volume(self.volume_input.text())
        speaker.pitch = self._normalize_pitch(self.pitch_input.text())
        self.speakers["TXT"] = speaker
        log_info(
            f"TXT mode apply voice={speaker.voice} segments={len(speaker.segments)} rate={speaker.rate} volume={speaker.volume} pitch={speaker.pitch}"
        )
        self.speakers_changed.emit()


def _compress_ranges(values: set[int]) -> str:
    if not values:
        return ""
    ordered = sorted(values)
    ranges: list[str] = []
    start = ordered[0]
    prev = ordered[0]
    for value in ordered[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = value
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)
