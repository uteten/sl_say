import os
import sys
import time
import logging
from typing import Generator

logger = logging.getLogger(__name__)


class FileWatcher:
    def __init__(self, file_path: str, interval: float = 0.5) -> None:
        self.file_path = file_path
        self.interval = interval
        self._running = True

    def stop(self) -> None:
        self._running = False

    def preview(self, lines: int = 5) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                tail = all_lines[-lines:] if len(all_lines) >= lines else all_lines
                logger.info("--- ログ末尾 %d 行 ---", len(tail))
                for line in tail:
                    logger.info("  %s", line.rstrip("\r\n"))
                logger.info("--- ここから監視開始 ---")
        except Exception:
            logger.exception("ログプレビューエラー")

    def _read_lines(self) -> list[str]:
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()

    def watch(self) -> Generator[str, None, None]:
        seen = len(self._read_lines())
        logger.info("初期行数: %d", seen)

        while self._running:
            try:
                lines = self._read_lines()
            except OSError:
                logger.warning("ファイル読み取りエラー（リトライします）")
                time.sleep(self.interval)
                continue

            if len(lines) < seen:
                # ファイルが短縮・ローテートされた場合はリセット
                logger.info("ファイル短縮を検出（%d -> %d 行）、先頭から再読み込み", seen, len(lines))
                seen = 0

            if len(lines) > seen:
                for line in lines[seen:]:
                    stripped = line.rstrip("\r\n").strip()
                    if stripped:
                        yield stripped
                seen = len(lines)
            time.sleep(self.interval)
