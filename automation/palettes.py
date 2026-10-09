from typing import Final, FrozenSet, Sequence, Tuple

from automation.dearpygui.items.colors import rounded_color
from sampletones_application.paths import PALETTES_DIRECTORY
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.palette import Palette

Color = Tuple[float, ...]
FULL_STEP: Final[float] = 255.0


def shipped_palettes() -> PaletteCatalog:
    """The palettes this build ships, the ones Display settings offers."""
    return PaletteCatalog.load(PALETTES_DIRECTORY)


def token_color(palette: Palette, token: str) -> Color:
    """The color ``token`` names in ``palette``, as DearPyGui holds it."""
    return in_fractions(palette.colors[token])


def in_fractions(color: Sequence[float]) -> Color:
    """A color given in whole steps, as DearPyGui holds it: each part a fraction of the full step."""
    return rounded_color(tuple(part / FULL_STEP for part in color))


def shared_colors(catalog: PaletteCatalog) -> FrozenSet[Color]:
    """Every color all the shipped palettes state alike under one token, which no palette swap changes."""
    palettes = tuple(catalog.palettes.values())
    first = palettes[0]
    return frozenset(
        token_color(first, token)
        for token in first.colors
        if all(palette.colors.get(token) == first.colors[token] for palette in palettes)
    )
