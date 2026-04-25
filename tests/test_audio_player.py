import sys
from unittest.mock import MagicMock, patch

from app.audio_player import AudioPlayer


class TestAudioPlayer:
    def setup_method(self) -> None:
        self.player = AudioPlayer()

    def test_is_available_returns_true(self) -> None:
        assert self.player.is_available() is True

    @patch("sys.platform", "win32")
    @patch("app.audio_player.ctypes")
    def test_play_calls_mci_sequence(self, mock_ctypes: MagicMock) -> None:
        mock_winmm = MagicMock()
        mock_winmm.mciSendStringW.return_value = 0
        mock_ctypes.windll.winmm = mock_winmm

        result = self.player.play("/tmp/test.mp3")
        assert result is True

        calls = mock_winmm.mciSendStringW.call_args_list
        assert len(calls) == 4
        assert "open" in calls[0][0][0]
        assert "setaudio" in calls[1][0][0]
        assert "volume" in calls[1][0][0]
        assert "play" in calls[2][0][0]
        assert "wait" in calls[2][0][0]
        assert "close" in calls[3][0][0]

    @patch("sys.platform", "win32")
    @patch("app.audio_player.ctypes")
    def test_play_error_returns_false_windows(self, mock_ctypes: MagicMock) -> None:
        mock_winmm = MagicMock()
        mock_winmm.mciSendStringW.side_effect = Exception("MCI error")
        mock_ctypes.windll.winmm = mock_winmm

        result = self.player.play("/tmp/test.mp3")
        assert result is False

    @patch("sys.platform", "darwin")
    @patch("app.audio_player.subprocess.run")
    def test_play_calls_afplay_on_macos(self, mock_run: MagicMock) -> None:
        result = self.player.play("/tmp/test.mp3")
        assert result is True
        mock_run.assert_called_once_with(["afplay", "-v", "1.0", "/tmp/test.mp3"], check=True)

    @patch("sys.platform", "darwin")
    @patch("app.audio_player.subprocess.run")
    def test_play_error_returns_false_macos(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = Exception("afplay error")
        result = self.player.play("/tmp/test.mp3")
        assert result is False
