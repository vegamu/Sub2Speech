import sys
from pathlib import Path

from sub2speech.utils.subprocess_utils import ensure_no_cmd_window

# Patch subprocess NGAY khi import module này, trước khi bất kỳ thư viện
# nào dưới đây (ffmpeg-python, imageio-ffmpeg, edge-tts, ...) kịp spawn
# tiến trình con. Nếu đặt muộn hơn, cửa sổ cmd vẫn có thể nhấp nháy trong
# những lần gọi đầu tiên của bản .exe windowed.
ensure_no_cmd_window()

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sub2speech.config import AppConfig  # noqa: E402
from sub2speech.ui.main_window import MainWindow  # noqa: E402
from sub2speech.utils.i18n import translator  # noqa: E402
from sub2speech.utils.logging_utils import init_logging, log_info  # noqa: E402


def _resolve_paths() -> tuple[Path, Path]:
    """Trả về (app_root, resource_root).

    - app_root: nơi ghi dữ liệu người dùng (config/, Audio/, temp/).
    - resource_root: nơi đọc tài nguyên tĩnh đi kèm (src/ico.png, ...).
    Khi chạy từ bản PyInstaller (frozen): app_root là thư mục chứa .exe,
    resource_root là _MEIPASS. Khi chạy nguồn: cả hai cùng trỏ về gốc repo.
    """
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).resolve().parent
        resource_root = Path(getattr(sys, "_MEIPASS", app_root))
    else:
        app_root = Path(__file__).resolve().parents[2]
        resource_root = app_root
    return app_root, resource_root


def _resolve_icon_path(app_root: Path, resource_root: Path) -> Path | None:
    candidates = [
        resource_root / "ico.png",
        resource_root / "src" / "ico.png",
        app_root / "src" / "ico.png",
        app_root / "ico.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    app_root, resource_root = _resolve_paths()
    logs_dir = init_logging(app_root)
    log_info(f"Sub2Speech started, logs dir={logs_dir}")
    config = AppConfig(app_root)
    settings = config.load_settings()
    translator.set_language(settings.language)
    app = QApplication(sys.argv)

    icon_path = _resolve_icon_path(app_root, resource_root)
    if icon_path is not None:
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)
        # Windows cần AppUserModelID để taskbar nhận đúng icon app.
        if sys.platform.startswith("win"):
            try:
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Sub2Speech.App")
            except Exception:
                pass
        log_info(f"Loaded application icon path={icon_path}")

    window = MainWindow(config)
    if icon_path is not None:
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
