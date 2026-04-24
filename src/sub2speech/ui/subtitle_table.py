from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from sub2speech.models.subtitle import Segment
from sub2speech.utils.i18n import tr, translator


class SubtitleTable(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 5)
        self._is_txt_mode = False
        self.retranslate_headers()
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        translator.language_changed.connect(self.retranslate_headers)

    def set_txt_mode(self, is_txt: bool) -> None:
        self._is_txt_mode = is_txt
        self.setColumnHidden(1, is_txt)

    def set_segments(
        self,
        segments: list[Segment],
        voice_map: dict[int, str],
        speaker_map: dict[int, str] | None = None,
    ) -> None:
        speaker_map = speaker_map or {}
        self.setRowCount(0)
        for seg in segments:
            row = self.rowCount()
            self.insertRow(row)
            self.setItem(row, 0, QTableWidgetItem(str(seg.index)))
            self.setItem(row, 1, QTableWidgetItem(f"{seg.start} --> {seg.end}"))
            self.setItem(row, 2, QTableWidgetItem(seg.text))
            speaker_name = seg.speaker or speaker_map.get(seg.index, "")
            self.setItem(row, 3, QTableWidgetItem(speaker_name))
            self.setItem(row, 4, QTableWidgetItem(voice_map.get(seg.index, "")))

    def retranslate_headers(self) -> None:
        self.setHorizontalHeaderLabels(
            [
                tr("table.idx"),
                tr("table.time"),
                tr("table.content"),
                tr("table.speaker"),
                tr("table.voice"),
            ]
        )
