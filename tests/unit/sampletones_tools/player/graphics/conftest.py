import pytest

from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.layout.screen import ScreenLayout
from sampletones_tools.player.graphics.sheet.patterns import sheet_patterns
from sampletones_tools.player.graphics.sheet.sheet import TileSheet


@pytest.fixture(name="shipped_sheet", scope="session")
def shipped_sheet_fixture() -> TileSheet:
    """The tile sheet the package ships."""
    return TileSheet.load()


@pytest.fixture(name="shipped_layout", scope="session")
def shipped_layout_fixture() -> ScreenLayout:
    """The screen layout the package ships."""
    return ScreenLayout.load()


@pytest.fixture(name="shipped_deck", scope="session")
def shipped_deck_fixture(shipped_layout: ScreenLayout, shipped_sheet: TileSheet) -> Deck:
    """The player screen the package ships, stated over its own layout and sheet."""
    return Deck(shipped_layout, shipped_sheet)


@pytest.fixture(name="shipped_patterns", scope="session")
def shipped_patterns_fixture(shipped_sheet: TileSheet) -> bytes:
    """Both pattern tables the shipped sheet draws."""
    return sheet_patterns(shipped_sheet)
