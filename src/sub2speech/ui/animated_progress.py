"""Thanh tiến trình có hiệu ứng gradient chạy liên tục.

Giữ nguyên hành vi của `QProgressBar` nhưng bổ sung một dải màu gradient
di chuyển trong phần đã fill, giúp người dùng biết tiến trình vẫn đang
hoạt động ngay cả khi phần trăm không thay đổi trong thời gian dài
(ví dụ: giai đoạn ffmpeg đang concat/mix audio cuối cùng).
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QProgressBar, QWidget


class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._offset = 0.0
        self._step = 0.025
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self.setTextVisible(True)
        self.setFormat("%p%")
        self.setMinimumHeight(18)
        self._apply_style()

    def _tick(self) -> None:
        self._offset = (self._offset + self._step) % 1.0
        self._apply_style()

    def _apply_style(self) -> None:
        # Dịch chuyển 3 stop của gradient theo offset để tạo cảm giác
        # "sóng" chạy dọc theo phần đã fill.
        left = max(0.0, self._offset - 0.35)
        right = min(1.0, self._offset + 0.35)
        self.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #eef2f7;
                text-align: center;
                color: #0f172a;
                font-weight: 600;
                min-height: 18px;
            }}
            QProgressBar::chunk {{
                border-radius: 8px;
                background: qlineargradient(
                    x1:{left:.3f}, y1:0, x2:{right:.3f}, y2:0,
                    stop:0 #93c5fd,
                    stop:0.5 #2563eb,
                    stop:1 #93c5fd
                );
            }}
            """
        )

    def showEvent(self, event) -> None:  # noqa: N802 - Qt signature
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt signature
        super().hideEvent(event)
        self._timer.stop()
