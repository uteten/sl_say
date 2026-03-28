import os
import tempfile

import pytest

from app.path_resolver import PathResolver


class TestPathResolver:
    def setup_method(self) -> None:
        self.resolver = PathResolver()

    def test_resolve_existing_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            result = self.resolver.resolve(path)
            assert result == path
        finally:
            os.unlink(path)

    def test_resolve_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.resolver.resolve("/tmp/nonexistent_chat_file_12345.txt")

    def test_resolve_none_returns_default_path(self) -> None:
        default = self.resolver._get_default_path()
        assert "Firestorm" in default or "firestorm" in default.lower()

    def test_no_wsl_path_conversion(self) -> None:
        # Windows paths should NOT be converted to WSL mount paths
        path = r"C:\Users\user\file.txt"
        # resolve will raise FileNotFoundError since path doesn't exist,
        # but we verify it doesn't attempt WSL conversion
        with pytest.raises(FileNotFoundError, match=r"C:\\Users\\user\\file\.txt"):
            self.resolver.resolve(path)
