from __future__ import annotations

from pathlib import Path
from typing import Dict

from pydantic import BaseModel

from sampletones_application.utils.palette.reference import REFERENCE_PREFIX, PaletteReference
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import RGBA, with_alpha_fraction
from sampletones_shared.utils.serialization import load_yaml


class Palette(BaseModel, frozen=True):
    """A named set of semantic colour tokens shared across a theme set and the layout.

    Colour fields reference these tokens by name so a colour is defined once and
    reused everywhere, and swapping the palette restyles every theme and layout entry
    that resolves against it.
    """

    name: str
    colors: Dict[str, RGBA]

    def resolve(self, reference: PaletteReference) -> ColorRGBA:
        """Resolve a reference to a concrete RGBA tuple.

        Applies the reference's alpha override when present, keeping the token's red,
        green, and blue channels.

        Raises:
            KeyError: when the palette holds no token of the referenced name.
        """
        if reference.token not in self.colors:
            raise KeyError(
                f"Palette {self.name!r} has no colour token {REFERENCE_PREFIX}{reference.token!r}. "
                f"Known tokens: {sorted(self.colors)}"
            )

        color = self.colors[reference.token]
        if reference.alpha is None:
            return color

        return with_alpha_fraction(color, reference.alpha)

    @classmethod
    def load(cls, path: Path) -> Palette:
        """Load the palette that colour references resolve against.

        Raises:
            TypeError: when the palette file holds a value other than a mapping.
            SystemError: when the file is not available.
        """
        try:
            raw = load_yaml(path)
        except OSError as exception:
            raise SystemError(f"Palette file '{path}' not found") from exception

        if not isinstance(raw, dict):
            raise TypeError(f"Palette file '{path}' must contain a mapping, got {type(raw)}")

        return Palette.model_validate(raw)
