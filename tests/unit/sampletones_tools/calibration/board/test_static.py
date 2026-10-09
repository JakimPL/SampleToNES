import re
from pathlib import Path
from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.board.layout import (
    DATA_FILE,
    FONTS_FILE,
    PAGE_DIRECTORY,
    PAGE_FILE,
    PALETTE_FILE,
    SCRIPT_FILE,
    SHIPPED_FILES,
    STYLE_FILE,
)
from sampletones_tools.calibration.board.palette import board_palette, palette_names
from sampletones_tools.calibration.board.paths import STATIC_DIRECTORY

REACHING_OUT: Final[Tuple[str, ...]] = (
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "sendBeacon",
    "http://",
    "https://",
    'src="//',
    'href="//',
)
REFERENCE: Final[re.Pattern[str]] = re.compile(r'(?:src|href)="([^"]+)"')
COLOR_LITERAL: Final[re.Pattern[str]] = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
TOKEN: Final[re.Pattern[str]] = re.compile(r"var\(--([a-z0-9_]+)\)")
REFEREE_NAMES: Final[Tuple[str, ...]] = ("mr-auditory", "mr-loudness", "zimtohrli")


def shipped(name: str) -> str:
    return (STATIC_DIRECTORY / name).read_text(encoding="utf-8")


class TestShippedFilesStayOffline:
    @pytest.mark.parametrize("name", SHIPPED_FILES)
    def test_a_shipped_file_reaches_nothing_beyond_the_page(self, name: str) -> None:
        content = shipped(name)

        assert [reaching for reaching in REACHING_OUT if reaching in content] == []

    @pytest.mark.parametrize("name", SHIPPED_FILES)
    def test_a_shipped_file_is_present(self, name: str) -> None:
        assert (STATIC_DIRECTORY / name).is_file()


class TestPageMarkup:
    def test_every_reference_is_relative(self) -> None:
        references = REFERENCE.findall(shipped(PAGE_FILE))

        assert references
        assert [reference for reference in references if Path(reference).is_absolute()] == []

    def test_the_page_names_exactly_the_files_the_layout_declares(self) -> None:
        expected = {
            f"{PAGE_DIRECTORY}/{name}" for name in (PALETTE_FILE, FONTS_FILE, STYLE_FILE, DATA_FILE, SCRIPT_FILE)
        }

        assert set(REFERENCE.findall(shipped(PAGE_FILE))) == expected


class TestStylesheetDrawsFromThePalette:
    def test_no_color_is_written_into_the_stylesheet(self) -> None:
        assert COLOR_LITERAL.findall(shipped(STYLE_FILE)) == []

    @pytest.mark.parametrize("name", palette_names())
    def test_every_token_it_names_exists_in_every_palette(self, name: str) -> None:
        colors = board_palette(name).colors
        named = set(TOKEN.findall(shipped(STYLE_FILE)))

        assert named
        assert [token for token in sorted(named) if token not in colors] == []


class TestScriptStatesNoMeasurement:
    @pytest.mark.parametrize("channel", list(ChannelName))
    def test_the_script_spells_no_channel(self, channel: ChannelName) -> None:
        assert channel.value not in shipped(SCRIPT_FILE)

    @pytest.mark.parametrize("referee", REFEREE_NAMES)
    def test_the_script_spells_no_referee(self, referee: str) -> None:
        assert referee not in shipped(SCRIPT_FILE)
