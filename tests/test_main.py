import os
import tempfile
import threading
import time
from unittest.mock import MagicMock

import pytest

from app.main import build_pipeline, needs_gui, parse_args


class TestParseArgs:
    def test_no_args_returns_none_path(self) -> None:
        args = parse_args([])
        assert args.file is None

    def test_file_arg(self) -> None:
        args = parse_args([r"C:\Users\user\chat.txt"])
        assert args.file == r"C:\Users\user\chat.txt"

    def test_voice_option(self) -> None:
        args = parse_args(["--voice", "ja-JP-KeitaNeural"])
        assert args.voice == "ja-JP-KeitaNeural"

    def test_default_voice(self) -> None:
        args = parse_args([])
        assert args.voice == "ja-JP-NanamiNeural"

    def test_rate_option(self) -> None:
        args = parse_args(["--rate", "+50%"])
        assert args.rate == "+50%"

    def test_default_rate(self) -> None:
        args = parse_args([])
        assert args.rate == "+0%"


class TestNeedsGui:
    def test_no_args_needs_gui(self) -> None:
        args = parse_args([])
        assert needs_gui(args) is True

    def test_file_arg_skips_gui(self) -> None:
        args = parse_args([r"C:\Users\user\chat.txt"])
        assert needs_gui(args) is False

    def test_rate_only_needs_gui(self) -> None:
        """--rate alone is an optional flag, not a positional arg, so GUI is still needed."""
        args = parse_args(["--rate", "+50%"])
        assert needs_gui(args) is True

    def test_voice_only_needs_gui(self) -> None:
        args = parse_args(["--voice", "ja-JP-KeitaNeural"])
        assert needs_gui(args) is True

    def test_file_with_options_skips_gui(self) -> None:
        args = parse_args([r"C:\chat.txt", "--rate", "+50%", "--voice", "ja-JP-KeitaNeural"])
        assert needs_gui(args) is False


class TestBuildPipeline:
    def test_pipeline_creates_watcher_and_queue(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("existing\n")
            path = f.name
        try:
            mock_engine = MagicMock()
            mock_player = MagicMock()

            watcher, tts_queue = build_pipeline(path, mock_engine, mock_player)
            assert watcher is not None
            assert tts_queue is not None
        finally:
            os.unlink(path)

    def test_pipeline_processes_new_lines(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("existing\n")
            path = f.name
        try:
            mock_engine = MagicMock()
            mock_engine.synthesize.return_value = "/tmp/fake.mp3"
            mock_player = MagicMock()
            mock_player.play.return_value = True

            watcher, tts_queue = build_pipeline(path, mock_engine, mock_player)
            tts_queue.start()

            def run_watcher() -> None:
                from app.chat_parser import ChatParser
                parser = ChatParser()
                for line in watcher.watch():
                    msg = parser.parse_line(line)
                    if msg:
                        tts_queue.enqueue(msg)

            t = threading.Thread(target=run_watcher, daemon=True)
            t.start()
            time.sleep(0.5)

            with open(path, "a") as f:
                f.write("[2026/03/26 14:05]  TestUser: こんにちは\n")

            time.sleep(1.5)
            watcher.stop()
            tts_queue.stop()
            t.join(timeout=3)

            mock_engine.synthesize.assert_called()
        finally:
            os.unlink(path)
