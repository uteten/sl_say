import os
import sys


def _default_firestorm_dir() -> str:
    if sys.platform == "win32":
        user = os.environ.get("USERNAME") or os.environ.get("USER", "user")
        return rf"C:\Users\{user}\AppData\Roaming\Firestorm_x64"
    elif sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Firestorm_x64")
    else:
        return os.path.expanduser("~/.firestorm_x64")


class PathResolver:
    def _get_default_path(self) -> str:
        return _default_firestorm_dir()

    def resolve(self, path: str | None) -> str:
        if path is None:
            resolved = self._get_default_path()
        else:
            resolved = path

        if not os.path.exists(resolved):
            raise FileNotFoundError(f"ファイルが見つかりません: {resolved}")
        return resolved
