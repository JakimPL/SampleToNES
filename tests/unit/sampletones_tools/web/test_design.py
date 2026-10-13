import pytest

from sampletones_tools.web.design import ApplicationDesign, palette_names


class TestApplicationDesign:
    def test_an_unknown_palette_is_refused(self) -> None:
        with pytest.raises(KeyError):
            ApplicationDesign.load("sunset")

    def test_the_glyph_characters_hold_every_glyph_once(self, design: ApplicationDesign) -> None:
        characters = design.glyph_characters

        assert design.glyphs.common.tick in characters
        assert design.glyphs.headers.reconstruction in characters
        assert len(set(characters)) == len(characters)


class TestPaletteNames:
    def test_the_shipped_palettes_are_listed(self) -> None:
        assert palette_names()
