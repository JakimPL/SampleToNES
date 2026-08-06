from typing import Any, Final, Mapping, Self, Union

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from sampletones_application.utils.palette.reference import PaletteReference, is_reference
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import parse_hex_color

PALETTE_SOURCE_CONTEXT_KEY: Final[str] = "palette_source"


def palette_source_from_context(info: ValidationInfo) -> PaletteSource:
    """The palette source a colour reference binds to, taken from the validation context.

    Raises:
        ValueError: when the context omits the palette source entry.
        TypeError: when the context entry holds a value other than a palette source.
    """
    context = info.context
    if not isinstance(context, Mapping) or PALETTE_SOURCE_CONTEXT_KEY not in context:
        raise ValueError(f"Resolving a palette reference requires a {PALETTE_SOURCE_CONTEXT_KEY!r} validation context")

    source = context[PALETTE_SOURCE_CONTEXT_KEY]
    if not isinstance(source, PaletteSource):
        raise TypeError(
            f"Validation context {PALETTE_SOURCE_CONTEXT_KEY!r} must be a PaletteSource, got {type(source)}"
        )

    return source


class NamedColor(BaseModel):
    """A palette reference together with the source that answers it."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    reference: PaletteReference
    source: PaletteSource

    @property
    def rgba(self) -> ColorRGBA:
        """The value the active palette gives the referenced token.

        Raises:
            KeyError: when that palette holds no token of the referenced name.
        """
        return self.source.palette.resolve(self.reference)


class PaletteColor(BaseModel):
    """A colour read at the moment it is drawn with.

    Written as a palette reference (``.token``, optionally ``.token/alpha``) or as a
    ``#rrggbb`` literal, and kept in the form it was written: a reference reads its
    value from the palette active right now, so the same field answers with a new
    colour once another palette is activated, while a literal stands on its own.
    Consumers read :attr:`rgba` where they hand the colour to DearPyGui, keeping the
    written form as the thing they hold on to.
    """

    model_config = ConfigDict(frozen=True)

    value: Union[NamedColor, ColorRGBA]

    @property
    def rgba(self) -> ColorRGBA:
        """The colour's value under the active palette."""
        if isinstance(self.value, NamedColor):
            return self.value.rgba

        return self.value

    @model_validator(mode="before")
    @classmethod
    def _from_written_color(cls, value: Any, info: ValidationInfo) -> object:
        if isinstance(value, str):
            text = value.strip()
            if is_reference(text):
                named = NamedColor(
                    reference=PaletteReference.model_validate(text),
                    source=palette_source_from_context(info),
                )
                return {"value": named}

            return {"value": parse_hex_color(text)}

        return value

    @model_validator(mode="after")
    def _resolve_once(self) -> Self:
        """Reads the colour once, so the palette in place at load answers for its token.

        Raises:
            KeyError: when that palette holds no token of the referenced name.
        """
        _ = self.rgba
        return self
