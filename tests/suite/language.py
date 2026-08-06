from dataclasses import dataclass, field
from typing import Mapping


@dataclass
class FakeLanguageManager:
    """A language manager answering each key with the key itself, or with a text stated for it.

    A test asserting on the text a widget or a callback receives then names the entry the code
    read, which holds the wiring in place while leaving the wording to the language file. Where
    the behaviour under test formats the text — a template with placeholders — the test states
    that text explicitly.
    """

    texts: Mapping[str, str] = field(default_factory=dict)

    def __getitem__(self, key: str) -> str:
        return self.texts.get(key, key)
