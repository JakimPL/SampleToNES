from functools import partial
from typing import Final

from automation.screen import Screen
from automation.steps.main import explorer_row, home_path
from automation.vocabulary.converter import CONVERT_NOTHING, CONVERT_ONE
from tests.screens.main.gathering.constants import INNER, LOOPS, TAKES
from tests.screens.main.gathering.steps import gathered
from tests.suite.screens.seeds.constants import KICK, SNARE

ADD_AS_STEM: Final[str] = "main.explorer.label.context_add_stem"


class TestNavigatingGathersNothing:
    """Opening folders in the explorer leaves the list empty; a double-click on a recording gathers that
    one.

    The scenario opens three folders and expects the hint, an empty list and the idle Convert button. A
    double-click on a recording then gives the list one row and names that recording on the button.
    """

    def test_the_list_stays_empty_until_a_recording_is_double_clicked(self, screen: Screen) -> None:
        """The list holds no row until a recording is double-clicked."""
        converter = screen.main.converter

        def open_folders(screen: Screen) -> None:
            for folder in (home_path(TAKES), home_path(TAKES) / INNER, home_path(LOOPS)):
                row = explorer_row(screen, folder)

                screen.explorer.open_by_click(row)

                screen.expect(partial(screen.explorer.is_open, row), bool, description=f"{folder.name} open")

        def the_list_stays_empty(screen: Screen) -> None:
            assert converter.list.hint_shown()
            assert not converter.list.list_shown()
            assert converter.action() == screen.words(CONVERT_NOTHING)

        def a_double_click_gathers_that_recording(screen: Screen) -> None:
            screen.explorer.double_click(explorer_row(screen, home_path(KICK)))

            gathered(screen, home_path(KICK))
            assert converter.action() == screen.words(CONVERT_ONE).format(name=home_path(KICK).stem)
            assert not converter.list.hint_shown()

        screen.scenario(open_folders, the_list_stays_empty, a_double_click_gathers_that_recording).run()


class TestAPlainClickOnARecording:
    """A plain click plays a recording; Ctrl-click and Add as stem gather it.

    A click starts playback and the hint stays. Ctrl-click on the same recording gathers it. Add as stem
    from another recording's menu gathers that one too, and the menu closes.
    """

    def test_it_plays_and_the_gathering_gestures_gather(self, screen: Screen) -> None:
        """A click only plays, while Ctrl-click and the Add as stem entry add rows."""
        converter = screen.main.converter

        def a_click_plays(screen: Screen) -> None:
            heard = screen.sound_heard()
            screen.explorer.click(explorer_row(screen, home_path(KICK)))

            screen.expect(screen.sound_heard, heard.__lt__, description="the recording heard")
            assert converter.list.hint_shown()

        def ctrl_click_gathers(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(KICK)))

            gathered(screen, home_path(KICK))

        def add_as_stem_gathers(screen: Screen) -> None:
            screen.explorer.right_click(explorer_row(screen, home_path(SNARE)))
            screen.expect(screen.context_menu.is_shown, bool, description="the recording's menu")

            screen.context_menu.choose(screen.words(ADD_AS_STEM))

            gathered(screen, home_path(KICK), home_path(SNARE))
            assert not screen.context_menu.is_shown()

        screen.scenario(a_click_plays, ctrl_click_gathers, add_as_stem_gathers).run()
