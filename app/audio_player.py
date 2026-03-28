import ctypes
import logging

logger = logging.getLogger(__name__)


class AudioPlayer:
    def __init__(self, volume: int = 100) -> None:
        self._volume = max(0, min(100, volume))

    def play(self, file_path: str) -> bool:
        try:
            winmm = ctypes.windll.winmm
            alias = "sl_say_audio"
            mci_volume = self._volume * 10  # 0-100 → 0-1000
            winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias {alias}', None, 0, 0)
            winmm.mciSendStringW(f"setaudio {alias} volume to {mci_volume}", None, 0, 0)
            winmm.mciSendStringW(f"play {alias} wait", None, 0, 0)
            winmm.mciSendStringW(f"close {alias}", None, 0, 0)
            return True
        except Exception:
            logger.exception("音声再生エラー")
            return False

    def is_available(self) -> bool:
        return True
