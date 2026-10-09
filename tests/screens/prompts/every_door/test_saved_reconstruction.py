import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.main import home_path
from automation.steps.reconstructions import converted, expect_open, load_from_the_browser, titled, voice_title
from tests.screens.prompts.every_door.cases import Door
from tests.screens.prompts.every_door.constants import SAMPLE_ORDINAL
from tests.screens.prompts.every_door.steps import expect_title, knock, nothing_asked
from tests.suite.screens.worlds.recordings import BASS, OPEN_RECONSTRUCTION, OTHER_RECONSTRUCTION, SONG, SONG_SAMPLE


class TestASavedReconstructionAtEveryDoor:
    """A reconstruction with nothing unsaved is put away at every door at once, and leaving leaves."""

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction beside a project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=SONG)

    def test_no_door_asks(self, screen: Screen) -> None:
        """Every door replaces, closes or leaves at once."""

        def the_browser_loads_at_once(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OPEN_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OPEN_RECONSTRUCTION.name))
            nothing_asked(screen)

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, converted(home_path(BASS)).name))
            nothing_asked(screen)

        def a_voice_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_SAMPLE)

            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False))
            nothing_asked(screen)

        def close_closes_at_once(screen: Screen) -> None:
            load_from_the_browser(screen, OPEN_RECONSTRUCTION)
            expect_open(screen, OPEN_RECONSTRUCTION)

            knock(screen, Door.CLOSE, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem))
            nothing_asked(screen)

        def the_window_closes_at_once(screen: Screen) -> None:
            load_from_the_browser(screen, OPEN_RECONSTRUCTION)
            expect_open(screen, OPEN_RECONSTRUCTION)

            knock(screen, Door.WINDOW_CLOSE, voice=SONG_SAMPLE)

            assert screen.wait_for_exit()

        screen.scenario(
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            the_conversion_loads_at_once,
            a_voice_opens_at_once,
            close_closes_at_once,
            the_window_closes_at_once,
        ).run()

    def test_exit_leaves_at_once(self, screen: Screen) -> None:
        """The exit shortcut leaves the application at once."""
        expect_open(screen, OPEN_RECONSTRUCTION)

        knock(screen, Door.EXIT, voice=SONG_SAMPLE)

        assert screen.wait_for_exit()
