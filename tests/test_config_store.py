import json
from pathlib import Path

import pytest

from app.config_store import AppConfig, ConfigStore


class TestAppConfig:
    def test_default_values(self) -> None:
        config = AppConfig()
        assert config.rate == "+0%"
        assert isinstance(config.file_path, str)

    def test_custom_values(self) -> None:
        config = AppConfig(file_path="C:\\test\\chat.txt", rate="+50%")
        assert config.file_path == "C:\\test\\chat.txt"
        assert config.rate == "+50%"


class TestConfigStore:
    def test_load_returns_default_when_file_missing(self, tmp_path: Path) -> None:
        store = ConfigStore(config_dir=tmp_path)
        config = store.load()
        assert config.rate == "+0%"
        assert isinstance(config.file_path, str)

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        store = ConfigStore(config_dir=tmp_path)
        original = AppConfig(file_path="C:\\my\\chat.txt", rate="-20%")
        store.save(original)
        loaded = store.load()
        assert loaded.file_path == original.file_path
        assert loaded.rate == original.rate

    def test_load_returns_default_when_json_corrupted(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        config_file.write_text("{invalid json!!!}", encoding="utf-8")
        store = ConfigStore(config_dir=tmp_path)
        config = store.load()
        assert config.rate == "+0%"

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        nested_dir = tmp_path / "nested" / "dir"
        store = ConfigStore(config_dir=nested_dir)
        store.save(AppConfig(file_path="C:\\test.txt", rate="+10%"))
        assert (nested_dir / "config.json").exists()

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        store = ConfigStore(config_dir=tmp_path)
        store.save(AppConfig(file_path="C:\\test.txt", rate="+30%"))
        data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
        assert data["file_path"] == "C:\\test.txt"
        assert data["rate"] == "+30%"

    def test_default_config_dir_uses_appdata(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("APPDATA", str(tmp_path))
        store = ConfigStore()
        assert store._config_dir == tmp_path / "sl_say"

    def test_default_config_dir_fallback_without_appdata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APPDATA", raising=False)
        store = ConfigStore()
        assert store._config_dir == Path(".sl_say")
