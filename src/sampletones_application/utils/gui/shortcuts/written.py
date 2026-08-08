from typing import Final, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut

NO_WRITTEN_ALIASES: Final[Tuple[str, ...]] = ()


class WrittenShortcut(BaseModel, frozen=True):
    """One action's binding as a keybinding file spells it out.

    The combination is written the way it reads on screen — ``"Ctrl+Shift+Z"``, ``"PgDn"``,
    ``"Num+"`` — so a reader assigns a key in the terms the menus already show them. An entry
    states its combination even where the action carries none, which keeps every action visible
    in the file and gives the keybindings options an entry to fill.
    """

    combination: Optional[str]
    aliases: Tuple[str, ...] = NO_WRITTEN_ALIASES
    field_transparent: bool = False

    def resolve(self) -> Shortcut:
        """The binding the entry names, read into the combinations a press is matched against.

        Raises:
            KeyError: when a written combination names a key the key table holds none of.
        """
        return Shortcut(
            combination=None if self.combination is None else KeyCombination.parse(self.combination),
            aliases=tuple(KeyCombination.parse(alias) for alias in self.aliases),
            field_transparent=self.field_transparent,
        )
