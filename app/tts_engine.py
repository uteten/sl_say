import asyncio
import logging
import tempfile

import edge_tts

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, voice: str = "ja-JP-NanamiNeural", rate: str = "+0%") -> None:
        self.voice = voice
        self.rate = rate

    def synthesize(self, text: str) -> str | None:
        if not text:
            return None
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            asyncio.run(communicate.save(tmp.name))
            return tmp.name
        except Exception:
            logger.exception("TTS合成エラー")
            return None
