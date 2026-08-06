from typing import Annotated, Any, Final, Mapping, Union

from pydantic import BeforeValidator, Field, ValidationInfo

from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.reference import PaletteReference, is_reference
from sampletones_shared.types.application import ColorRGBA
from sampletones_shared.utils.color import RGBA, parse_hex_color

PALETTE_CONTEXT_KEY: Final[str] = "palette"

ColorSource = Annotated[Union[PaletteReference, RGBA], Field(union_mode="left_to_right")]


def palette_from_context(info: ValidationInfo) -> Palette:
    """The palette a colour field resolves against, taken from the validation context.

    Raises:
        ValueError: when the context omits the palette entry.
        TypeError: when the context entry holds a value other than a palette.
    """
    context = info.context
    if not isinstance(context, Mapping) or PALETTE_CONTEXT_KEY not in context:
        raise ValueError(f"Resolving a palette reference requires a {PALETTE_CONTEXT_KEY!r} validation context")

    palette = context[PALETTE_CONTEXT_KEY]
    if not isinstance(palette, Palette):
        raise TypeError(f"Validation context {PALETTE_CONTEXT_KEY!r} must be a Palette, got {type(palette)}")

    return palette


def _resolve_palette_color(value: Any, info: ValidationInfo) -> object:
    if isinstance(value, str):
        text = value.strip()
        if is_reference(text):
            return palette_from_context(info).resolve(PaletteReference.model_validate(text))

        return parse_hex_color(text)

    return value


PaletteColor = Annotated[ColorRGBA, BeforeValidator(_resolve_palette_color)]
