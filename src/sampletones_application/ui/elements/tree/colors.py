from dataclasses import dataclass
from typing import Self

from sampletones_application.layout.general.colors import GeneralColors
from sampletones_application.utils.palette.color import PaletteColor


@dataclass(frozen=True)
class TreeColors:
    """Colors a tree panel uses to render node labels and context-menu headers.

    ``accent`` highlights config-bearing nodes (libraries, reconstruction directories) and varies
    per browser, while the others are shared across browsers.
    """

    favorite: PaletteColor
    node: PaletteColor
    muted: PaletteColor
    accent: PaletteColor

    @classmethod
    def create(cls, colors: GeneralColors, *, accent: PaletteColor) -> Self:
        """Assigns shared palette entries to tree roles; only ``accent`` differs between browsers.

        Defining the shared mapping in one place keeps every browser's favorite/node/muted colors
        consistent by construction; the caller supplies the one role that legitimately varies.
        """
        return cls(
            favorite=colors.favorites.default,
            node=colors.paths.hover,
            muted=colors.text.disabled,
            accent=accent,
        )
