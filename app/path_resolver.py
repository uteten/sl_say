import os


class PathResolver:
    DEFAULT_DIR_TEMPLATE = r"C:\Users\{user}\AppData\Roaming\Firestorm_x64"

    def _get_default_path(self) -> str:
        user = os.environ.get("USERNAME") or os.environ.get("USER", "user")
        return self.DEFAULT_DIR_TEMPLATE.format(user=user)

    def resolve(self, path: str | None) -> str:
        if path is None:
            resolved = self._get_default_path()
        else:
            resolved = path

        if not os.path.exists(resolved):
            raise FileNotFoundError(f"ファイルが見つかりません: {resolved}")
        return resolved
