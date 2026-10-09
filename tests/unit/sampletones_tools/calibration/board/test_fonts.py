from pathlib import Path
from typing import Final

import pytest

from sampletones_tools.calibration.board.fonts import (
    FONT_MEDIA_TYPE,
    PAGE_FONTS,
    PageFont,
    fonts_stylesheet,
)
from sampletones_tools.calibration.board.paths import FONTS_DIRECTORY

FACE_RULE: Final[str] = "@font-face"


class TestFontsStylesheet:
    def test_every_face_carries_its_own_data(self) -> None:
        stylesheet = fonts_stylesheet()

        assert stylesheet.count(FACE_RULE) == len(PAGE_FONTS)
        assert stylesheet.count(f"data:{FONT_MEDIA_TYPE};base64,") == len(PAGE_FONTS)

    @pytest.mark.parametrize("font", PAGE_FONTS, ids=lambda font: font.filename)
    def test_a_face_names_the_family_and_weight_it_answers_at(self, font: PageFont) -> None:
        stylesheet = fonts_stylesheet()

        assert f'font-family: "{font.family}";' in stylesheet
        assert f"font-weight: {font.weight};" in stylesheet

    @pytest.mark.parametrize("font", PAGE_FONTS, ids=lambda font: font.filename)
    def test_the_assets_hold_the_face_it_reads(self, font: PageFont) -> None:
        assert (FONTS_DIRECTORY / font.filename).is_file()

    def test_a_missing_face_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            fonts_stylesheet(tmp_path)
