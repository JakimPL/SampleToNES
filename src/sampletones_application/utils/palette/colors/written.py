from typing import Annotated, Final, Mapping

from pydantic import PlainValidator, ValidationInfo

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.utils.palette.colors.named import NamedColor
from sampletones_application.utils.palette.reference import PaletteReference, is_reference
from sampletones_application.utils.palette.source import PaletteSource
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


def _written_color(value: object, info: ValidationInfo) -> BaseColor:
    """The colour a configuration entry spells out, read once so its token answers at load.

    An entry is written as a palette reference (``.token``, optionally ``.token/alpha``) or
    as a ``#rrggbb`` literal, and is kept in the form it was written. A colour built in code
    passes through as it stands, which is how a derived shade reaches a field.

    Raises:
        ValueError: when the entry holds a value of some other kind.
        KeyError: when the palette in place at load holds no token of the referenced name.
    """
    if isinstance(value, BaseColor):
        return value

    if not isinstance(value, str):
        raise ValueError(f"A colour is written as a palette reference or a hex literal, got {type(value)}")

    text = value.strip()
    color: BaseColor
    if is_reference(text):
        color = NamedColor(
            reference=PaletteReference.model_validate(text),
            source=palette_source_from_context(info),
        )
    else:
        color = LiteralColor(parse_hex_color(text))

    _ = color.rgba
    return color


WrittenColor = Annotated[BaseColor, PlainValidator(_written_color)]
