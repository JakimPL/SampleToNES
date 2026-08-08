from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Dict, List, Self, Tuple

from pydantic import BaseModel, model_validator

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut
from sampletones_shared.utils.serialization import load_yaml


class ShortcutScheme(BaseModel, frozen=True):
    """A named set of keybindings, one entry per action the application names.

    The scheme is where a combination is decided: an action declares the id it answers to, and the
    scheme alone says which keys reach it. Every action is answered here, so the combination a menu
    prints, the one a panel acts on and the one a reader edits are the same entry.
    """

    name: str
    bindings: Dict[ShortcutId, WrittenShortcut]

    @cached_property
    def shortcuts(self) -> Dict[ShortcutId, Shortcut]:
        """Every action's binding, read out of its written form once."""
        return {shortcut_id: written.resolve() for shortcut_id, written in self.bindings.items()}

    @model_validator(mode="after")
    def _read_bindings(self) -> Self:
        """Reads every entry at load, so a scheme in use answers each action with keys that resolve
        and with one action per combination.

        Raises:
            SystemError: when an action goes unanswered, or two actions of one category claim the
                same combination.
            KeyError: when a written combination names a key the key table holds none of.
        """
        self._require_every_action_answered()
        self._require_one_action_per_combination()
        return self

    def shortcut(self, shortcut_id: ShortcutId) -> Shortcut:
        """The binding that answers an action, the combinations it names ready to match a press."""
        return self.shortcuts[shortcut_id]

    @classmethod
    def load(cls, path: Path) -> ShortcutScheme:
        """Load the scheme a keybinding file holds.

        Raises:
            TypeError: when the file holds a value other than a mapping.
            SystemError: when the file is not available.
        """
        try:
            raw = load_yaml(path)
        except OSError as exception:
            raise SystemError(f"Keybinding file '{path}' not found") from exception

        if not isinstance(raw, dict):
            raise TypeError(f"Keybinding file '{path}' must contain a mapping, got {type(raw)}")

        return cls.model_validate(raw)

    def _require_every_action_answered(self) -> None:
        unanswered: List[str] = [shortcut_id.value for shortcut_id in ShortcutId if shortcut_id not in self.bindings]
        if unanswered:
            raise SystemError(f"Keybinding scheme {self.name!r} leaves actions unanswered: {unanswered}")

    def _require_one_action_per_combination(self) -> None:
        claimed: Dict[Tuple[ShortcutCategory, KeyCombination], ShortcutId] = {}
        for shortcut_id, shortcut in self.shortcuts.items():
            for combination in shortcut.combinations():
                claim = (shortcut_id.category, combination)
                if claim in claimed:
                    raise SystemError(
                        f"Keybinding scheme {self.name!r} gives {combination.display()} to both "
                        f"{claimed[claim].value!r} and {shortcut_id.value!r}, "
                        f"which share the {shortcut_id.category} category"
                    )

                claimed[claim] = shortcut_id
