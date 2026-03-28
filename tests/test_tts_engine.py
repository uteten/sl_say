import os
from unittest.mock import AsyncMock, patch

from app.tts_engine import TTSEngine


class TestTTSEngine:
    def setup_method(self) -> None:
        self.engine = TTSEngine()

    def test_default_voice_is_japanese(self) -> None:
        assert "ja-JP" in self.engine.voice

    @patch("app.tts_engine.edge_tts.Communicate")
    def test_synthesize_returns_file_path(self, mock_communicate_cls: object) -> None:
        mock_instance = AsyncMock()
        mock_instance.save = AsyncMock()
        mock_communicate_cls.return_value = mock_instance  # type: ignore[union-attr]

        result = self.engine.synthesize("こんにちは")
        assert result is not None
        assert result.endswith(".mp3")
        if os.path.exists(result):
            os.unlink(result)

    @patch("app.tts_engine.edge_tts.Communicate")
    def test_synthesize_error_returns_none(self, mock_communicate_cls: object) -> None:
        mock_instance = AsyncMock()
        mock_instance.save = AsyncMock(side_effect=Exception("network error"))
        mock_communicate_cls.return_value = mock_instance  # type: ignore[union-attr]

        result = self.engine.synthesize("test")
        assert result is None

    def test_synthesize_empty_text_returns_none(self) -> None:
        result = self.engine.synthesize("")
        assert result is None
