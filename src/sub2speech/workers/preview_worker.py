import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from sub2speech.config import AppConfig
from sub2speech.core.edge_tts_engine import synthesize_sync
from sub2speech.utils.logging_utils import log_error, log_info


class PreviewWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        config: AppConfig,
        text: str,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        super().__init__()
        self.config = config
        self.text = text
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    def run(self) -> None:
        try:
            output = Path(self.config.temp_dir) / f"preview_{int(time.time() * 1000)}.mp3"
            log_info(
                f"Preview synthesize voice={self.voice} rate={self.rate} volume={self.volume} pitch={self.pitch} out={output}"
            )
            synthesize_sync(
                self.text,
                self.voice,
                str(output),
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch,
            )
            log_info(f"Preview done out={output}")
            self.finished.emit(str(output))
        except Exception as exc:
            log_error(f"Preview failed: {exc}")
            self.error.emit(str(exc))
