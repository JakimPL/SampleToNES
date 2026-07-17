from pathlib import Path
from typing import Dict, Tuple, Union, overload

from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_shared.utils.serialization import load_yaml

TextKeyTuple = Tuple[Page, Panel, TextType, AbstractElement]


class LanguageManager:
    def __init__(self, language_path: Path) -> None:
        self._data: Dict[str, str] = {}
        self.load(language_path)

    def load(self, path: Path) -> None:
        raw = load_yaml(path)
        if not isinstance(raw, dict):
            raise TypeError(f"Language file must contain a mapping, got {type(raw)}")

        self._data = {str(key): str(value) for key, value in raw.items()}

    @overload
    def __getitem__(self, key: TextKey) -> str: ...
    @overload
    def __getitem__(self, key: TextKeyTuple) -> str: ...
    def __getitem__(self, key: Union[TextKey, TextKeyTuple]) -> str:
        if not isinstance(key, TextKey):
            key = TextKey(*key)

        return self._data[key.compose()]
