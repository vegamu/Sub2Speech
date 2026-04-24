import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    output_dir: str
    save_original_audio: bool
    last_language_group: str
    language: str
    tts_concurrency: int


class AppConfig:
    def __init__(self, app_root: Path) -> None:
        self.app_root = app_root
        self.config_dir = app_root / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.config_dir / "settings.json"
        self.voices_cache_path = self.config_dir / "voices_cache.json"
        self.audio_root = app_root / "Audio"
        self.audio_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = app_root / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def load_settings(self) -> Settings:
        default = Settings(
            output_dir=str(self.audio_root.resolve()),
            save_original_audio=False,
            last_language_group="Tiếng Việt",
            language="vi",
            tts_concurrency=2,
        )
        if not self.settings_path.exists():
            return default
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return Settings(
                output_dir=raw.get("output_dir", default.output_dir),
                save_original_audio=bool(raw.get("save_original_audio", default.save_original_audio)),
                last_language_group=raw.get("last_language_group", default.last_language_group),
                language=raw.get("language", default.language),
                tts_concurrency=self._clamp_tts_concurrency(raw.get("tts_concurrency", default.tts_concurrency)),
            )
        except (OSError, json.JSONDecodeError):
            return default

    def save_settings(self, settings: Settings) -> None:
        payload = {
            "output_dir": settings.output_dir,
            "save_original_audio": settings.save_original_audio,
            "last_language_group": settings.last_language_group,
            "language": settings.language,
            "tts_concurrency": self._clamp_tts_concurrency(settings.tts_concurrency),
        }
        self.settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _clamp_tts_concurrency(value: object) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 2
        return max(1, min(parsed, 8))
