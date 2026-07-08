from __future__ import annotations

from pathlib import Path
from typing import Dict, Final, Optional

from pydantic import BaseModel, model_validator

from sampletones_application.utils.color import RGBA
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.serialization import load_yaml

REFERENCE_PREFIX: Final[str] = "."
ALPHA_SEPARATOR: Final[str] = "/"

_OPAQUE_ALPHA: Final[int] = 255


class PaletteReference(BaseModel, frozen=True):
    """A theme entry's reference to a named palette colour.

    Written in YAML as ``.token`` or ``.token/alpha`` where ``alpha`` is a fraction
    in ``[0, 1]`` that overrides the token's own alpha. The leading ``.`` marks the
    value as a reference and keeps it distinct from a ``#rrggbb`` literal, so a
    theme entry accepts either form in the same field.
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
    """A named set of semantic colour tokens shared across a theme set.

    Theme entries reference these tokens by name so a colour is defined once and
    reused everywhere, and swapping the palette restyles every theme that resolves
    against it.
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

        red, green, blue, token_alpha = self.colors[reference.token]
        if reference.alpha is None:
            return (red, green, blue, token_alpha)

        return (red, green, blue, round(reference.alpha * _OPAQUE_ALPHA))

    @classmethod
    def load(cls, path: Path) -> Palette:
        """Load the palette that theme entries in ``theme_directory`` resolve against.

        A directory that omits a palette file resolves to an empty palette, so a theme
        set that states every colour as a literal loads without one.

        Raises:
            TypeError: when the palette file holds a value other than a mapping.
        """
        if not path.exists():
            raise SystemError(f"Palette file '{path}' not found")

        raw = load_yaml(path)
        if not isinstance(raw, dict):
            raise TypeError(f"Palette file '{path}' must contain a mapping, got {type(raw)}")

        return Palette.model_validate(raw)
