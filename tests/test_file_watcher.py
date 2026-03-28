import os
import tempfile
import threading
import time

from app.file_watcher import FileWatcher


class TestFileWatcher:
    def test_starts_from_end_of_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("existing line 1\n")
            f.write("existing line 2\n")
            path = f.name
        try:
            watcher = FileWatcher(path, interval=0.1)
            lines: list[str] = []

            def collect() -> None:
                for line in watcher.watch():
                    lines.append(line)
                    if len(lines) >= 1:
                        watcher.stop()

            t = threading.Thread(target=collect)
            t.start()
            time.sleep(0.3)
            with open(path, "a") as f:
                f.write("new line\n")
            t.join(timeout=3)
            assert lines == ["new line"]
        finally:
            os.unlink(path)

    def test_detects_new_lines(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            watcher = FileWatcher(path, interval=0.1)
            lines: list[str] = []

            def collect() -> None:
                for line in watcher.watch():
                    lines.append(line)
                    if len(lines) >= 2:
                        watcher.stop()

            t = threading.Thread(target=collect)
            t.start()
            time.sleep(0.3)
            with open(path, "a") as f:
                f.write("line1\n")
                f.write("line2\n")
            t.join(timeout=3)
            assert lines == ["line1", "line2"]
        finally:
            os.unlink(path)

    def test_normalizes_crlf(self) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            watcher = FileWatcher(path, interval=0.1)
            lines: list[str] = []

            def collect() -> None:
                for line in watcher.watch():
                    lines.append(line)
                    if len(lines) >= 1:
                        watcher.stop()

            t = threading.Thread(target=collect)
            t.start()
            time.sleep(0.3)
            with open(path, "ab") as f:
                f.write(b"hello\r\n")
            t.join(timeout=3)
            assert lines == ["hello"]
        finally:
            os.unlink(path)
