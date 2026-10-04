from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, List, Set, Tuple

from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.keys import (
    is_named_key,
    key_code,
    key_display,
)
from sampletones_application.utils.gui.keyboard.modifiers import (
    MODIFIER_NAMES,
    NO_MODIFIERS,
    Modifier,
    ModifierSet,
    modifiers_display,
)

COMBINATION_SEPARATOR: Final[str] = "+"
KEY_LIST_SEPARATOR: Final[str] = ","
KEY_LIST_JOINER: Final[str] = ", "


@dataclass(frozen=True)
class KeyCombination:
    """A key together with the modifiers a press holds to reach it.

    One combination answers both questions asked of a binding: how it reads wherever it is shown,
    and whether a given press is the one it names. Writing it out and reading it back arrive at the
    same combination, so a binding declared in code and one written in configuration are one value.
    """

    key: int
    modifiers: ModifierSet = NO_MODIFIERS

    @property
    def is_writable(self) -> bool:
        """Whether the combination reads back as itself once written down.

        A combination is built from whatever code a press reports, while a binding is kept as text,
        so an entry a scheme can hold is one whose key the table names.
        """
        return is_named_key(self.key)

    def matches(self, event: KeyEvent) -> bool:
        """Whether ``event`` is a press of this combination.

        Args:
            event: The press to test, carrying the modifiers held as it fired.

        Returns:
            bool: True while the event names this key under exactly these modifiers.
        """
        return event.key == self.key and event.modifiers == self.modifiers

    def display(self) -> str:
        """The combination as it reads, its modifiers in canonical order ahead of the key."""
        return COMBINATION_SEPARATOR.join((*modifiers_display(self.modifiers), key_display(self.key)))

    @classmethod
    def parse(cls, text: str) -> KeyCombination:
        """The combination a written form such as ``"Ctrl+Shift+Z"`` names.

        Leading parts that name a modifier are read as modifiers and everything after them is the
        key, so a key written with the separator itself keeps it: ``"Ctrl++"`` reads as Ctrl and the
        plus key.

        Args:
            text: A combination as :meth:`display` writes it, in any capitalization.

        Returns:
            KeyCombination: The combination the text names.

        Raises:
            KeyError: If the part left after the modifiers names no key.
        """
        parts = text.split(COMBINATION_SEPARATOR)
        modifiers: Set[Modifier] = set()
        index = 0
        while index < len(parts) - 1 and parts[index].casefold() in MODIFIER_NAMES:
            modifiers.add(MODIFIER_NAMES[parts[index].casefold()])
            index += 1

        return cls(
            key=key_code(COMBINATION_SEPARATOR.join(parts[index:])),
            modifiers=frozenset(modifiers),
        )


def combination_parts(text: str) -> Tuple[str, ...]:
    """The combinations a written list such as ``"Ctrl+Y, Ctrl+Shift+Z"`` names, each as it is written.

    A comma separates two combinations, and a comma written where a key goes is the comma key: one
    after the modifiers of a combination, as in ``"Ctrl+,"``, and one standing alone before a
    separator or the end of the list. Each part is trimmed, and a blank part names nothing. A list
    is displayed with the comma key spelled ``Comma``, so a displayed list reads back as itself.
    """
    parts: List[str] = []
    part = ""
    for index, character in enumerate(text):
        if character == KEY_LIST_SEPARATOR and not _is_comma_key(part, text[index + 1 :]):
            parts.append(part)
            part = ""
        else:
            part += character

    parts.append(part)
    return tuple(part.strip() for part in parts if part.strip())


def _is_comma_key(written: str, rest: str) -> bool:
    """Whether a comma after ``written`` and ahead of ``rest`` in one part of a list is a key."""
    before = written.strip()
    if before:
        return _awaits_key(before)

    after = rest.lstrip()
    return not after or after.startswith(KEY_LIST_SEPARATOR)


def _awaits_key(written: str) -> bool:
    """Whether ``written`` names modifiers alone, each followed by the separator, so its key comes next."""
    if not written.endswith(COMBINATION_SEPARATOR):
        return False

    return all(
        part.casefold() in MODIFIER_NAMES
        for part in written.removesuffix(COMBINATION_SEPARATOR).split(COMBINATION_SEPARATOR)
    )


def parse_combinations(text: str) -> Tuple[KeyCombination, ...]:
    """The combinations a written list names, in the order it names them, each one once.

    Raises:
        KeyError: If a part of the list names no key.
    """
    return tuple(dict.fromkeys(KeyCombination.parse(part) for part in combination_parts(text)))


def display_combinations(combinations: Iterable[KeyCombination]) -> str:
    """The combinations as a list reads them, in their order and joined by commas."""
    return KEY_LIST_JOINER.join(combination.display() for combination in combinations)
