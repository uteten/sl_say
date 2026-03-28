import sys
from unittest.mock import MagicMock, patch

from app.audio_player import AudioPlayer


class TestAudioPlayer:
    def setup_method(self) -> None:
        self.player = AudioPlayer()

    def test_is_available_returns_true(self) -> None:
        # MCI API is always available on Windows; on non-Windows we still return True
        assert self.player.is_available() is True

    @patch("app.audio_player.ctypes")
    def test_play_calls_mci_sequence(self, mock_ctypes: MagicMock) -> None:
        mock_winmm = MagicMock()
        mock_winmm.mciSendStringW.return_value = 0
        mock_ctypes.windll.winmm = mock_winmm

        result = self.player.play("/tmp/test.mp3")
        assert result is True

        calls = mock_winmm.mciSendStringW.call_args_list
        assert len(calls) == 4
        # open command
        assert "open" in calls[0][0][0]
        # setaudio volume command
        assert "setaudio" in calls[1][0][0]
        assert "volume" in calls[1][0][0]
        # play wait command
        assert "play" in calls[2][0][0]
        assert "wait" in calls[2][0][0]
        # close command
        assert "close" in calls[3][0][0]

    @patch("app.audio_player.ctypes")
    def test_play_error_returns_false(self, mock_ctypes: MagicMock) -> None:
        mock_winmm = MagicMock()
        mock_winmm.mciSendStringW.side_effect = Exception("MCI error")
        mock_ctypes.windll.winmm = mock_winmm

        result = self.player.play("/tmp/test.mp3")
        assert result is False
