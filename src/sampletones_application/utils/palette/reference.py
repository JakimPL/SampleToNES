from typing import Any, Dict, Final, Optional

from pydantic import BaseModel, model_validator

REFERENCE_PREFIX: Final[str] = "."
ALPHA_SEPARATOR: Final[str] = "/"


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
    def _from_string(cls, value: Any) -> object:
        if isinstance(value, str):
            return parse_reference(value)

        return value


def parse_reference(value: str) -> Dict[str, object]:
    """Split a written reference into the fields :class:`PaletteReference` validates.

    Raises:
        ValueError: when the text lacks the reference prefix, names no token, or
            carries an alpha outside ``[0, 1]``.
    """
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


def is_reference(value: str) -> bool:
    return value.strip().startswith(REFERENCE_PREFIX)
