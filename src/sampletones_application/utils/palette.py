from __future__ import annotations

from pathlib import Path
from typing import Annotated, Dict, Final, Mapping, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field, ValidationInfo, model_validator

from sampletones_application.utils.color import RGBA, parse_hex_color, with_alpha_fraction
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.serialization import load_yaml

REFERENCE_PREFIX: Final[str] = "."
ALPHA_SEPARATOR: Final[str] = "/"
PALETTE_CONTEXT_KEY: Final[str] = "palette"


class PaletteReference(BaseModel, frozen=True):
    """A colour entry's reference to a named palette colour.

    Written in YAML as ``.token`` or ``.token/alpha`` where ``alpha`` is a fraction
    in ``[0, 1]`` that overrides the token's own alpha. The leading ``.`` marks the
    value as a reference and keeps it distinct from a ``#rrggbb`` literal, so a
    colour field accepts either form in the same slot.
    """

    token: str
    alpha: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def _from_string(cls, value: object) -> object:
        if isinstance(value, str):
            return _parse_reference(value)

        return value


def _parse_reference(value: str) -> Dict[str, object]:
    text = value.strip()
    if not text.startswith(REFERENCE_PREFIX):
        raise ValueError(f"Palette reference must start with {REFERENCE_PREFIX!r}, got {value!r}")

    token, separator, alpha_text = text[len(REFERENCE_PREFIX) :].partition(ALPHA_SEPARATOR)
    if not token:
        raise ValueError(f"Palette reference must name a token, got {value!r}")

    parsed: Dict[str, object] = {"token": token}
    if separator:
        alpha = float(alpha_text)
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"Palette reference alpha must lie within [0, 1], got {alpha} in {value!r}")
        parsed["alpha"] = alpha

    return parsed


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


ColorSource = Annotated[Union[PaletteReference, RGBA], Field(union_mode="left_to_right")]


def _palette_from_context(info: ValidationInfo) -> Palette:
    context = info.context
    if not isinstance(context, Mapping) or PALETTE_CONTEXT_KEY not in context:
        raise ValueError(f"Resolving a palette reference requires a {PALETTE_CONTEXT_KEY!r} validation context")

    palette = context[PALETTE_CONTEXT_KEY]
    if not isinstance(palette, Palette):
        raise TypeError(f"Validation context {PALETTE_CONTEXT_KEY!r} must be a Palette, got {type(palette)}")

    return palette


def _resolve_palette_color(value: object, info: ValidationInfo) -> object:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(REFERENCE_PREFIX):
            return _palette_from_context(info).resolve(PaletteReference.model_validate(text))

        return parse_hex_color(text)

    return value


PaletteColor = Annotated[ColorRGBA, BeforeValidator(_resolve_palette_color)]
"""A colour field accepting a ``#rrggbb`` literal or a ``.token`` palette reference.

References resolve against the :class:`Palette` supplied under ``PALETTE_CONTEXT_KEY`` in
the Pydantic validation context, so a validated field always holds a concrete RGBA tuple.
"""
