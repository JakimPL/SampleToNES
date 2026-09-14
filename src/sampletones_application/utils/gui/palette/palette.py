from itertools import chain
from typing import ClassVar, Dict, Final, Iterator

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.palette.binding import (
    COLOR_ARGUMENT,
    ArgumentBinding,
    ArgumentKey,
    PaletteBinding,
    ThemeColorBinding,
)
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import Sender

PRUNE_FLOOR: Final[int] = 256


class PaletteBindings:
    """Every color DearPyGui holds a copy of, and the token each copy came from.

    DearPyGui reads an item's color argument and a theme color item once, at the call that
    fills it, so those copies keep the shade of the palette that was active then. Handing a
    color over through this registry keeps the :class:`BaseColor` alongside the copy, and
    :meth:`apply` hands DearPyGui the value each token carries now.

    One argument of one item holds one color, so binding it again replaces what is recorded
    for it: an item recolored on every hover stays a single entry. Items come and go with every
    menu and every rebuild, so the registry lets the deleted ones go whenever it has doubled since
    it last did, which keeps it to the items alive at a cost spread over the binds.
    """

    _arguments: ClassVar[Dict[ArgumentKey, ArgumentBinding]] = {}
    _theme_colors: ClassVar[Dict[Sender, ThemeColorBinding]] = {}
    _pruned_at: ClassVar[int] = PRUNE_FLOOR

    @classmethod
    def bind(
        cls,
        item: Sender,
        color: BaseColor,
        *,
        argument: str = COLOR_ARGUMENT,
    ) -> None:
        """Colors one of an item's arguments now, and keeps the token behind it."""
        binding = ArgumentBinding(
            item=item,
            color=color,
            argument=argument,
        )
        binding.push()
        cls._arguments[item, argument] = binding
        cls._prune_once_doubled()

    @classmethod
    def bind_theme_color(cls, item: Sender, color: BaseColor) -> None:
        """Keeps the token behind a theme color item the caller has just filled."""
        cls._theme_colors[item] = ThemeColorBinding(
            item=item,
            color=color,
        )
        cls._prune_once_doubled()

    @classmethod
    def apply(cls) -> None:
        """Hands DearPyGui the value every registered token carries now.

        Bindings whose item has since been deleted are dropped first, so only live items are
        colored.
        """
        cls._prune()
        for binding in cls.bindings():
            binding.push()

    @classmethod
    def _prune_once_doubled(cls) -> None:
        if cls._size() >= 2 * cls._pruned_at:
            cls._prune()

    @classmethod
    def _prune(cls) -> None:
        """Lets go of the bindings whose item has been deleted."""
        cls._arguments = {key: binding for key, binding in cls._arguments.items() if cls._is_live(binding)}
        cls._theme_colors = {key: binding for key, binding in cls._theme_colors.items() if cls._is_live(binding)}
        cls._pruned_at = max(PRUNE_FLOOR, cls._size())

    @classmethod
    def _size(cls) -> int:
        return len(cls._arguments) + len(cls._theme_colors)

    @classmethod
    def bindings(cls) -> Iterator[PaletteBinding]:
        """Every color copy the registry currently tracks."""
        return chain(cls._arguments.values(), cls._theme_colors.values())

    @classmethod
    def clear(cls) -> None:
        cls._arguments.clear()
        cls._theme_colors.clear()
        cls._pruned_at = PRUNE_FLOOR

    @staticmethod
    def _is_live(binding: PaletteBinding) -> bool:
        return bool(dpg.does_item_exist(binding.item))
