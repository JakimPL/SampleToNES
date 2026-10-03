import operator
from functools import partial
from typing import Final

import dearpygui.dearpygui as dpg

from tests.screens.main.list.constants import FORTY, FORTY_COUNT
from tests.screens.main.list.steps import gather, recording, take
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.dearpygui.items.regions import read_scroll
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import choose_from_the_row_menu, home_path
from tests.suite.screens.vocabulary.converter import FOLDER_ROW
from tests.suite.screens.vocabulary.recordings import KICK

STILL_FRAMES: Final[int] = 30
SHOW_RECORDINGS: Final[str] = "main.converter.label.context_open_folder"
HIDE_RECORDINGS: Final[str] = "main.converter.label.context_close_folder"


class TestAFolderInTheList:
    """A gathered folder arrives closed; its marker, a double-click on its name and its menu each open and
    close it.
    """

    def test_each_gesture_opens_and_closes_it(self, screen: Screen) -> None:
        """Each gesture opens the folder and the same gesture closes it again."""
        listing = screen.main.converter.list
        folder = home_path(FORTY)

        def arrives_closed(screen: Screen) -> None:
            gather(screen, folder)

            assert not listing.is_open(folder)

        def the_marker(screen: Screen) -> None:
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="open by its marker")

            listing.toggle_folder(folder)

            screen.expect(partial(listing.is_open, folder), operator.not_, description="closed by its marker")

        def a_double_click_on_its_name(screen: Screen) -> None:
            screen.hand.double_click(listing.row(folder))
            screen.expect(partial(listing.is_open, folder), bool, description="open by a double-click")

            screen.hand.double_click(listing.row(folder))

            screen.expect(partial(listing.is_open, folder), operator.not_, description="closed by a double-click")

        def its_menu(screen: Screen) -> None:
            choose_from_the_row_menu(screen, folder, screen.words(SHOW_RECORDINGS))
            screen.expect(partial(listing.is_open, folder), bool, description="open from its menu")

            choose_from_the_row_menu(screen, folder, screen.words(HIDE_RECORDINGS))

            screen.expect(partial(listing.is_open, folder), operator.not_, description="closed from its menu")

        screen.scenario(arrives_closed, the_marker, a_double_click_on_its_name, its_menu).run()


class TestAFolderThatScrolls:
    """An open folder of forty scrolls in its own region, end to end, and its rows hold still under the
    pointer.

    The folder opens beside a recording. The wheel takes it to the last row while the outer list keeps
    its scroll. The pointer then rests on that row for thirty frames and its rectangle stays the same.
    """

    def test_it_scrolls_on_its_own_to_its_last_row(self, screen: Screen) -> None:
        """The folder scrolls to its last row in its own region."""
        listing = screen.main.converter.list
        folder = home_path(FORTY)
        region = listing.tags.region(str(folder))
        last = folder / take(FORTY_COUNT - 1)

        def open_it(screen: Screen) -> None:
            gather(screen, home_path(KICK), folder)
            listing.toggle_folder(folder)

            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")
            assert screen.bridge.ask(lambda: read_scroll(region)).maximum > 0

        def the_wheel_takes_it_to_its_last_row(screen: Screen) -> None:
            well_before = screen.bridge.ask(lambda: read_scroll(listing.tags.well))

            screen.hand.scroll_to_end(region)

            screen.expect(partial(listing.has_row, last), bool, description="the last row drawn")
            screen.hand.scroll_into_view(listing.row(last))
            screen.hand.hover(listing.row(last))
            assert screen.bridge.ask(lambda: read_scroll(listing.tags.well)) == well_before

        def rows_hold_still_under_the_pointer(screen: Screen) -> None:
            row = listing.row(last)
            screen.hand.hover(row)

            with screen.record(lambda: read_item(row).rect) as recording:
                screen.frames(STILL_FRAMES)

            assert len(set(recording.values())) == 1, recording.values()

        screen.scenario(open_it, the_wheel_takes_it_to_its_last_row, rows_hold_still_under_the_pointer).run()


class TestRemovingFolders:
    """Removing a recording inside an open folder, or the folder itself, takes exactly what it names."""

    def test_a_recording_inside_goes_alone_and_the_folder_counts_one_fewer(self, screen: Screen) -> None:
        """Only the chosen recording goes; the folder stays open, counts one fewer and the other rows are
        kept.
        """
        listing = screen.main.converter.list
        folder = home_path(FORTY)
        removed = folder / take(1)

        def open_the_folder_beside_a_recording(screen: Screen) -> None:
            gather(screen, home_path(KICK), folder)
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

        def remove_one_inside(screen: Screen) -> None:
            outside = screen.bridge.ask(lambda: dpg.get_alias_id(listing.row(home_path(KICK))))

            listing.remove(removed)

            screen.expect(partial(listing.has_row, removed), operator.not_, description="the recording gone")
            expected = screen.words(FOLDER_ROW).format(name=folder.name, count=FORTY_COUNT - 1)
            screen.expect(partial(listing.label, folder), expected.__eq__, description="the folder counting one fewer")
            assert listing.has_row(folder / take(0)) and listing.has_row(folder / take(2))
            assert listing.is_open(folder)
            assert screen.bridge.ask(lambda: dpg.get_alias_id(listing.row(home_path(KICK)))) == outside

        screen.scenario(open_the_folder_beside_a_recording, remove_one_inside).run()

    def test_an_open_folder_goes_with_its_recordings_and_comes_back_closed(self, screen: Screen) -> None:
        """The folder leaves with its recordings, and gathering it again brings it back closed."""
        listing = screen.main.converter.list
        folder = home_path(FORTY)

        def remove_it_open(screen: Screen) -> None:
            gather(screen, home_path(KICK), folder)
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

            listing.remove(folder)

            screen.expect(partial(listing.has_row, folder), operator.not_, description="the folder gone")
            assert listing.rows() == [listing.row(home_path(KICK))]

        def gather_it_again(screen: Screen) -> None:
            gather(screen, folder)

            assert not listing.is_open(folder)
            assert listing.rows() == [listing.row(home_path(KICK)), listing.row(folder)]

        screen.scenario(remove_it_open, gather_it_again).run()
