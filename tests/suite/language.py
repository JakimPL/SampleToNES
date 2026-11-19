from dataclasses import dataclass, field
from typing import Mapping, Union

from sampletones_application.categories.key.text import (
    TextKey,
    TextKeyTuple,
    compose_text_key,
)

LanguageKey = Union[str, TextKey, TextKeyTuple]


@dataclass
class FakeLanguageManager:
    """A language manager answering each key with the key itself, or with a text stated for it.

    A test asserting on the text a widget or a callback receives then names the entry the code
    read, which holds the wiring in place while leaving the wording to the language file. Where
    the behavior under test formats the text — a template with placeholders — the test states
    that text explicitly, under the key in whichever form the code reads it. A key assembled from
    its hierarchy members and stated for nothing answers as the dotted key it spells, the way the
    language file is keyed.
    """

    texts: Mapping[LanguageKey, str] = field(default_factory=dict)

    def __getitem__(self, key: LanguageKey) -> str:
        if key in self.texts:
            return self.texts[key]

        composed = compose_text_key(key)
        return self.texts.get(composed, composed)
