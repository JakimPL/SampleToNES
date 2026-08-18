from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from sampletones_shared.utils.color import parse_hex_color


def _validate_hex_color(value: str) -> str:
    parse_hex_color(value)
    return value


HexColor = Annotated[str, AfterValidator(_validate_hex_color)]


class MarkBackground(BaseModel, extra="forbid", frozen=True):
    """The vertical gradient filling the frame."""

    top: HexColor = Field(description="Colour at the top edge of the frame.")
    bottom: HexColor = Field(description="Colour at the bottom edge of the frame.")


class MarkColors(BaseModel, extra="forbid", frozen=True):
    """The mark's colours, written as the hex strings the vector carries."""

    background: MarkBackground = Field(description="Gradient behind the wave.")
    sine: HexColor = Field(description="Colour of the smooth half of the wave.")
    square: HexColor = Field(description="Colour of the stepped half of the wave.")
    rim: HexColor = Field(description="Colour of the hairline inside the frame's edge.")
