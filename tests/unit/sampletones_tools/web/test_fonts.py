from pathlib import Path
from typing import Final

import pytest

from sampletones_tools.web.fonts import (
    FONT_MEDIA_TYPE,
    ICON_FONT,
    PAGE_FONTS,
    PageFont,
    fonts_stylesheet,
    unicode_range,
)
from sampletones_tools.web.paths import FONTS_DIRECTORY

FACE_RULE: Final[str] = "@font-face"
GLYPHS: Final[str] = "▍▾▸"


class TestFontsStylesheet:
    def test_every_face_carries_its_own_data(self) -> None:
        stylesheet = fonts_stylesheet(FONTS_DIRECTORY, GLYPHS)

        assert stylesheet.count(FACE_RULE) == len(PAGE_FONTS) + 1
        assert stylesheet.count(f"data:{FONT_MEDIA_TYPE};base64,") == len(PAGE_FONTS) + 1

    @pytest.mark.parametrize("font", (*PAGE_FONTS, ICON_FONT), ids=lambda font: f"{font.filename}-{font.style}")
    def test_the_assets_hold_the_face_it_reads(self, font: PageFont) -> None:
        assert (FONTS_DIRECTORY / font.filename).is_file()

    def test_only_the_glyph_face_is_limited_to_the_glyphs(self) -> None:
        stylesheet = fonts_stylesheet(FONTS_DIRECTORY, GLYPHS)

        assert stylesheet.count("unicode-range:") == 1
        assert f"unicode-range: {unicode_range(GLYPHS)};" in stylesheet

    def test_a_missing_face_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            fonts_stylesheet(tmp_path, GLYPHS)


class TestUnicodeRange:
    def test_consecutive_code_points_join_into_a_span(self) -> None:
        assert unicode_range("cab") == "U+0061-0063"

    def test_apart_code_points_stay_apart(self) -> None:
        assert unicode_range("▸▍") == "U+258D, U+25B8"
