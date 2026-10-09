import re
from typing import Dict, Final

import pytest

from sampletones_tools.calibration.board.palette import (
    CHANNEL_TOKEN_PREFIX,
    board_palette,
    channel_token,
    css_color,
    palette_names,
    palette_stylesheet,
)

DECLARATION: Final[re.Pattern[str]] = re.compile(r"--([a-z0-9_]+): (#[0-9a-f]{6}(?:[0-9a-f]{2})?);")


def declared(stylesheet: str) -> Dict[str, str]:
    return dict(DECLARATION.findall(stylesheet))


class TestPaletteStylesheet:
    @pytest.mark.parametrize("name", palette_names())
    def test_every_token_reaches_the_page_under_its_own_name(self, name: str) -> None:
        palette = board_palette(name)

        written = declared(palette_stylesheet(palette))

        assert written == {token: css_color(color) for token, color in palette.colors.items()}

    def test_an_unknown_palette_is_refused(self) -> None:
        with pytest.raises(KeyError):
            board_palette("sunset")


class TestCssColor:
    def test_an_opaque_color_is_six_digits(self) -> None:
        assert css_color((26, 27, 38, 255)) == "#1a1b26"

    def test_a_translucent_color_carries_its_alpha(self) -> None:
        assert css_color((26, 27, 38, 170)) == "#1a1b26aa"


class TestChannelToken:
    def test_a_channel_stands_under_the_prefix_the_palette_uses(self) -> None:
        assert channel_token("noise") == f"{CHANNEL_TOKEN_PREFIX}noise"
