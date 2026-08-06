from pathlib import Path
from typing import Dict, Union, overload

from sampletones_application.categories.key.grammar import validate_text_key
from sampletones_application.categories.key.text import (
    TextKey,
    TextKeyTuple,
    compose_text_key,
)
from sampletones_shared.exceptions import MissingTextError
from sampletones_shared.utils.serialization import load_yaml


class LanguageManager:
    """Interface text, keyed the way the language file spells it.

    A lookup takes the dotted key itself — `language_manager["global.dialog.label.ok"]` — which is
    what the `language-keys` hook reads to hold code and language file to each other. The
    `TextKey` and four-member tuple forms serve a key assembled at runtime, where an enum member
    arrives in a variable.
    """

    def __init__(self, language_path: Path) -> None:
        self._language_path: Path
        self._data: Dict[str, str] = {}
        self.load(language_path)

    def load(self, path: Path) -> None:
        """Replaces the held text with the contents of a language file.

        Args:
            path: Language file to read.

        Raises:
            TypeError: If the file holds anything other than a mapping.
            MalformedTextKeyError: If any key in the file departs from the text-key grammar.
        """
        raw = load_yaml(path)
        if not isinstance(raw, dict):
            raise TypeError(f"Language file must contain a mapping, got {type(raw)}")

        data = {str(key): str(value) for key, value in raw.items()}
        for key in data:
            validate_text_key(key)

        self._language_path = path
        self._data = data

    @overload
    def __getitem__(self, key: str) -> str: ...

    @overload
    def __getitem__(self, key: TextKey) -> str: ...

    @overload
    def __getitem__(self, key: TextKeyTuple) -> str: ...

    def __getitem__(self, key: Union[str, TextKey, TextKeyTuple]) -> str:
        composed = compose_text_key(key)
        text = self._data.get(composed)
        if text is None:
            validate_text_key(composed)
            raise MissingTextError(f"Language file {self._language_path} holds no text for key {composed!r}")

        return text
