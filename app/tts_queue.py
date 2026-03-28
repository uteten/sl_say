import logging
import os
import queue
import threading

from app.audio_player import AudioPlayer
from app.chat_parser import ChatMessage
from app.filter_config import FilterConfig
from app.tts_engine import TTSEngine

logger = logging.getLogger(__name__)


class TTSQueue:
    def __init__(
        self,
        engine: TTSEngine,
        player: AudioPlayer,
        filter_config: FilterConfig | None = None,
    ) -> None:
        self.engine = engine
        self.player = player
        self._filter = filter_config or FilterConfig(exclude_patterns=[], replace_rules=[])
        self._queue: queue.Queue[ChatMessage | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def enqueue(self, message: ChatMessage) -> None:
        self._queue.put(message)

    def _format_text(self, message: ChatMessage) -> str:
        if message.message_type == "emote":
            text = f"{message.speaker} {message.body}"
        else:
            text = f"{message.speaker}: {message.body}"
        return self._filter.apply_replacements(text)

    def _worker(self) -> None:
        while True:
            message = self._queue.get()
            if message is None:
                break
            try:
                text = self._format_text(message)
                audio_path = self.engine.synthesize(text)
                if audio_path:
                    self.player.play(audio_path)
                    try:
                        os.unlink(audio_path)
                    except OSError:
                        pass
            except Exception:
                logger.exception("TTS処理エラー")
