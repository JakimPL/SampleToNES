from functools import partial
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.paths import LAYOUT_DIRECTORY
from sampletones_shared.utils.serialization import load_yaml_model
from tests.screens.main.list.constants import FREQUENCY
from tests.screens.main.list.steps import gather
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.vocabulary.converter import FOLDER_ROW, REMOVE_RECORDING
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import lived_in_world

THOUSANDS: Final[str] = "Thousands"
THOUSANDS_COUNT: Final[int] = 1500
TINY_SECONDS: Final[float] = 0.01
ONE_ROW: Final[int] = 1
STEMS_LAYOUT: Final[Path] = LAYOUT_DIRECTORY / "general" / "stems.yaml"
MENU_ROW: Final[int] = 3
WHEEL_PAST: Final[int] = 5


def thousand(index: int) -> str:
    """Returns the file name of the numbered recording in the folder of thousands."""
    return f"take{index:04d}.wav"


def rows_inside(screen: Screen, folder: Path) -> List[str]:
    """Returns the rows of ``folder`` that the list draws at this moment, in list order."""
    listing = screen.main.converter.list
    inside = {listing.row(folder / thousand(index)) for index in range(THOUSANDS_COUNT)}
    return [row for row in listing.rows() if row in inside]


class TestAFolderOfThousands:
    """A folder of thousands opens drawing only the rows in view; its last row and any row menu still
    answer.

    The folder is gathered and opened. One scenario scrolls to the last row. The other opens a row's
    menu, turns the wheel, chooses Remove and expects that row alone to be gone.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds one folder of 1500 tiny recordings."""
        files = [
            Recording(destination=home_path(THOUSANDS) / thousand(index), seconds=TINY_SECONDS, frequency=FREQUENCY)
            for index in range(THOUSANDS_COUNT)
        ]
        return World(state=lived_in_world().state, application_config=None, config=None, files=tuple(files))

    def open_it(self, screen: Screen) -> None:
        """Gathers the folder of thousands and opens it in the list."""
        listing = screen.main.converter.list
        gather(screen, home_path(THOUSANDS))
        listing.toggle_folder(home_path(THOUSANDS))
        screen.expect(partial(listing.is_open, home_path(THOUSANDS)), bool, description="the folder open")

    def test_it_draws_the_rows_in_view_and_reaches_its_last(self, screen: Screen) -> None:
        """The drawn rows fill the region plus the overscan, and scrolling to the end draws the last row."""
        listing = screen.main.converter.list
        folder = home_path(THOUSANDS)
        region = listing.tags.region(str(folder))
        last = folder / thousand(THOUSANDS_COUNT - 1)

        def opens_drawing_what_is_in_view(screen: Screen) -> None:
            self.open_it(screen)
            drawn = rows_inside(screen, folder)
            region_box = screen.bridge.ask(lambda: read_item(region).rect)
            first = screen.bridge.ask(lambda: read_item(drawn[0]).rect)
            second = screen.bridge.ask(lambda: read_item(drawn[1]).rect)
            assert region_box is not None and first is not None and second is not None
            pitch = second.y - first.y
            overscan = load_yaml_model(STEMS_LAYOUT, StemsListLayout).window_overscan

            assert len(drawn) <= int(region_box.height / pitch) + ONE_ROW + 2 * overscan

        def reaches_the_last_row(screen: Screen) -> None:
            screen.hand.scroll_to_end(region)

            screen.expect(partial(listing.has_row, last), bool, description="the last row drawn")
            screen.hand.scroll_into_view(listing.row(last))
            screen.hand.hover(listing.row(last))

        screen.scenario(opens_drawing_what_is_in_view, reaches_the_last_row).run()

    def test_remove_chosen_after_the_wheel_turned_removes_the_row_the_menu_was_opened_on(self, screen: Screen) -> None:
        """The menu stays open while the wheel turns, and Remove deletes the row it was opened on."""
        listing = screen.main.converter.list
        menu = screen.context_menu
        folder = home_path(THOUSANDS)
        region = listing.tags.region(str(folder))
        target = folder / thousand(MENU_ROW)

        def open_the_menu_and_turn_the_wheel(screen: Screen) -> None:
            self.open_it(screen)
            screen.hand.scroll_into_view(listing.row(target))
            screen.hand.right_click(listing.row(target))
            screen.expect(menu.is_shown, bool, description="the row's menu")

            screen.hand.turn_wheel_over(region, WHEEL_PAST)

            assert menu.is_shown()

        def remove_from_the_menu(screen: Screen) -> None:
            menu.choose(screen.words(REMOVE_RECORDING))

            expected = screen.words(FOLDER_ROW).format(name=folder.name, count=THOUSANDS_COUNT - 1)
            screen.expect(partial(listing.label, folder), expected.__eq__, description="one row fewer")

        def that_row_alone_went(screen: Screen) -> None:
            screen.hand.turn_wheel_over(region, -2 * WHEEL_PAST)
            screen.expect(partial(listing.has_row, folder / thousand(0)), bool, description="the top in view")

            assert not listing.has_row(target)
            assert listing.has_row(folder / thousand(MENU_ROW - 1)) and listing.has_row(folder / thousand(MENU_ROW + 1))

        screen.scenario(open_the_menu_and_turn_the_wheel, remove_from_the_menu, that_row_alone_went).run()
