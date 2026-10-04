from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel


class KeybindingRow(BaseModel, frozen=True):
    """One action as the keybindings dialog lists it: its name, its label, and the keys it answers.

    An action travels under the name a keybinding file writes it by, which is the identity a stored
    preference is keyed by as well, so a row states which action it stands for in the terms the view
    reads. Its keys read as a list joined by commas, main key first, and empty while it is unbound.
    """

    action: str
    label: str
    keys: str

    def matches(self, text: str) -> bool:
        """Whether the row answers a filter, which reads both what it is called and what it answers.

        Args:
            text: What the reader typed, matched in any capitalization.

        Returns:
            bool: True while the label or the keys hold the text, and for an empty filter.
        """
        wanted = text.strip().casefold()
        return wanted in self.label.casefold() or wanted in self.keys.casefold()


class KeybindingGroup(BaseModel, frozen=True):
    """The actions of one scope, under the name a reader finds that scope by.

    A scope is a keyboard context of its own, so grouping by it is what tells a reader that the
    same combination reaching two rows is two separate keys rather than a clash. The scope travels
    under its own name beside the label, which lets a view address a group whatever it is called.
    """

    category: str
    label: str
    rows: Tuple[KeybindingRow, ...]


class KeybindingsViewModel(BaseModel, frozen=True):
    """What the keybindings dialog draws: the actions listed, the selection standing, and its state.

    The dialog edits a draft the owner holds, so what shows here is the draft. It reaches the keys
    the application runs under when the reader confirms. ``keys`` is what the entry box shows: the
    selected action's keys joined by commas.
    """

    groups: Tuple[KeybindingGroup, ...]
    schemes: Tuple[str, ...]
    scheme: str
    selected: Optional[str]
    keys: str
    message: str
