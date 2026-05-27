from pathlib import Path

from sampletones_application.text.key import TextKey
from sampletones_shared.utils.serialization import load_yaml


class LanguageManager:
    def __init__(self, language_path: Path) -> None:
        self._data: dict[str, str] = {}
        self.load(language_path)

    def load(self, path: Path) -> None:
        raw = load_yaml(path)
        if not isinstance(raw, dict):
            raise TypeError(f"Language file must contain a mapping, got {type(raw)}")
        self._data = {str(key): str(value) for key, value in raw.items()}

    def __getitem__(self, key: TextKey) -> str:
        return self._data[key.compose()]
