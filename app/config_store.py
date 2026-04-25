import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _default_file_path() -> str:
    from app.path_resolver import _default_firestorm_dir
    return _default_firestorm_dir()


@dataclass
class AppConfig:
    file_path: str = field(default_factory=_default_file_path)
    rate: str = "+0%"
    volume: int = 100


class ConfigStore:
    _CONFIG_FILENAME = "config.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is not None:
            self._config_dir = config_dir
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA", "")
            self._config_dir = Path(appdata) / "sl_say" if appdata else Path.home() / "AppData" / "Roaming" / "sl_say"
        elif sys.platform == "darwin":
            self._config_dir = Path.home() / "Library" / "Application Support" / "sl_say"
        else:
            self._config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "sl_say"

    @property
    def _config_path(self) -> Path:
        return self._config_dir / self._CONFIG_FILENAME

    def load(self) -> AppConfig:
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            return AppConfig(
                file_path=data.get("file_path", _default_file_path()),
                rate=data.get("rate", "+0%"),
                volume=data.get("volume", 100),
            )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        data = {"file_path": config.file_path, "rate": config.rate, "volume": config.volume}
        self._config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
