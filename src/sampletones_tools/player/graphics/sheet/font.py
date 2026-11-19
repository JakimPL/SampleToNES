from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.specification.screen import FIRST_GLYPH, GLYPH_COUNT
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.player.graphics.paths import FONT_PATH
from sampletones_tools.player.graphics.sheet.drawing import Drawing


class Font(BaseModel):
    """The glyph every printable character is drawn as.

    Attributes:
        first: The code of the first character drawn.
        glyphs: Each character's drawing, by its code.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    first: int
    glyphs: Dict[int, Drawing]

    @model_validator(mode="after")
    def _validate_the_font_covers_the_printable_characters(self) -> Font:
        expected = set(range(FIRST_GLYPH, FIRST_GLYPH + GLYPH_COUNT))
        if self.first != FIRST_GLYPH or set(self.glyphs) != expected:
            raise ValueError(f"the font draws the {GLYPH_COUNT} characters from {FIRST_GLYPH:#04x} on, each once")

        return self

    @classmethod
    def load(cls) -> Font:
        """The font the package ships."""
        return load_yaml_model(FONT_PATH, cls)

    def draws(self, character: str) -> bool:
        """Whether the font holds a glyph for ``character``."""
        return ord(character) in self.glyphs

    def glyph(self, character: str) -> Drawing:
        """The drawing of one character.

        Raises:
            KeyError: If the font draws no such character.
        """
        return self.glyphs[ord(character)]
