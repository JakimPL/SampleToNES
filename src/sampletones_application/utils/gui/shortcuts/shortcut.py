from dataclasses import dataclass
from typing import Final, Optional, Tuple

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent

NO_COMBINATION: Final[str] = ""
NO_ALIASES: Final[Tuple[KeyCombination, ...]] = ()


@dataclass(frozen=True)
class Shortcut:
    """The binding of one action: the combination that fires it, the further ones that also do, and
    whether it fires while a field is focused.

    The primary combination is the one the action displays in menus and tooltips; an alias extends
    only the key handling, so one action answers several conventional combinations. An action holds
    a binding record whether or not a combination is assigned to it, so a menu lists it either way
    and the keybindings options have an entry to fill.

    ``field_transparent`` shortcuts (e.g. switching tabs) outrank text entry and fire even while an
    input owns the keyboard; the rest stay behind field focus so their keys reach the field.
    """

    combination: Optional[KeyCombination]
    aliases: Tuple[KeyCombination, ...] = NO_ALIASES
    field_transparent: bool = False

    def combinations(self) -> Tuple[KeyCombination, ...]:
        """Every combination that fires the action, the one it displays first."""
        primary = () if self.combination is None else (self.combination,)
        return (*primary, *self.aliases)

    def matches(self, event: KeyEvent) -> bool:
        """Whether ``event`` is a press of any combination bound to the action.

        Args:
            event: The press to test, carrying the modifiers held as it fired.

        Returns:
            bool: True while any bound combination names the event.
        """
        return any(combination.matches(event) for combination in self.combinations())

    def display(self) -> str:
        """The combination as it reads in a menu, empty while the action carries none."""
        return NO_COMBINATION if self.combination is None else self.combination.display()
