import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from sub2speech.config import AppConfig
from sub2speech.ui.main_window import MainWindow
from sub2speech.utils.logging_utils import log_info


def _resolve_paths() -> tuple[Path, Path]:
    """Trả về (app_root, resource_root).

    - app_root: nơi ghi dữ liệu người dùng (config/, Audio/, temp/).
    - resource_root: nơi đọc tài nguyên tĩnh đi kèm (ico.png, ...).
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


def main() -> int:
    app_root, resource_root = _resolve_paths()
    app = QApplication(sys.argv)

    icon_path = resource_root / "ico.png"
    if icon_path.exists():
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

    config = AppConfig(app_root)
    window = MainWindow(config)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
