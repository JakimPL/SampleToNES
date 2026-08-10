from itertools import chain
from typing import ClassVar, Dict, Iterator

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


class PaletteBindings:
    """Every colour DearPyGui holds a copy of, and the token each copy came from.

    DearPyGui reads an item's colour argument and a theme colour item once, at the call that
    fills it, so those copies keep the shade of the palette that was active then. Handing a
    colour over through this registry keeps the :class:`BaseColor` alongside the copy, and
    :meth:`apply` hands DearPyGui the value each token carries now.

    One argument of one item holds one colour, so binding it again replaces what is recorded
    for it: an item recoloured on every hover stays a single entry.
    """

    _arguments: ClassVar[Dict[ArgumentKey, ArgumentBinding]] = {}
    _theme_colors: ClassVar[Dict[Sender, ThemeColorBinding]] = {}

    @classmethod
    def bind(
        cls,
        item: Sender,
        color: BaseColor,
        *,
        argument: str = COLOR_ARGUMENT,
    ) -> None:
        """Colours one of an item's arguments now, and keeps the token behind it."""
        binding = ArgumentBinding(
            item=item,
            color=color,
            argument=argument,
        )
        binding.push()
        cls._arguments[item, argument] = binding

    @classmethod
    def bind_theme_color(cls, item: Sender, color: BaseColor) -> None:
        """Keeps the token behind a theme colour item the caller has just filled."""
        cls._theme_colors[item] = ThemeColorBinding(
            item=item,
            color=color,
        )

    @classmethod
    def apply(cls) -> None:
        """Hands DearPyGui the value every registered token carries now.

        Bindings whose item has since been deleted are dropped, so the registry tracks the
        items that are alive and a long session's worth of transient widgets leaves nothing
        behind.
        """
        cls._arguments = {key: binding for key, binding in cls._arguments.items() if cls._is_live(binding)}
        cls._theme_colors = {key: binding for key, binding in cls._theme_colors.items() if cls._is_live(binding)}
        for binding in cls.bindings():
            binding.push()

    @classmethod
    def bindings(cls) -> Iterator[PaletteBinding]:
        """Every colour copy the registry currently tracks."""
        return chain(cls._arguments.values(), cls._theme_colors.values())

    @classmethod
    def clear(cls) -> None:
        cls._arguments.clear()
        cls._theme_colors.clear()

    @staticmethod
    def _is_live(binding: PaletteBinding) -> bool:
        return bool(dpg.does_item_exist(binding.item))
