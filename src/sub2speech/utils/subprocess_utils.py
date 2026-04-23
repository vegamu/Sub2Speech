"""Tiện ích liên quan tới việc chạy tiến trình con (subprocess).

Mục đích chính: ngăn các tiến trình con (ffmpeg, ffprobe, ...) hiển thị cửa
sổ console nhấp nháy khi ứng dụng chạy ở chế độ GUI, đặc biệt trong bản
PyInstaller windowed (.exe). Trên Windows, mỗi lệnh `subprocess.Popen`
không có `creationflags` hợp lệ đều có thể bật một cửa sổ cmd rồi tắt
ngay, gây khó chịu cho người dùng.
"""

from __future__ import annotations

import subprocess
import sys

_PATCHED = False


def ensure_no_cmd_window() -> None:
    """Monkey-patch `subprocess.Popen` để ẩn cửa sổ console trên Windows.

    - Chỉ tác động trên nền Windows (`sys.platform == "win32"`).
    - An toàn khi gọi nhiều lần: chỉ patch một lần duy nhất.
    - Áp dụng cho toàn bộ `subprocess.Popen`, gồm cả các lệnh mà
      `ffmpeg-python` / `imageio-ffmpeg` gọi ngầm bên dưới.
    """
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    if sys.platform != "win32":
        return

    create_no_window = 0x08000000
    original_init = subprocess.Popen.__init__

    def patched_init(self, *args, **kwargs):
        creationflags = kwargs.get("creationflags", 0) or 0
        kwargs["creationflags"] = creationflags | create_no_window
        if kwargs.get("startupinfo") is None:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo
        return original_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = patched_init  # type: ignore[assignment]
