import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.prompts.every_door.cases import Door
from tests.screens.prompts.every_door.constants import SAMPLE_ORDINAL
from tests.screens.prompts.every_door.steps import expect_title, knock, nothing_asked
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import home_path
from tests.suite.screens.steps.reconstructions import converted, titled, voice_title
from tests.suite.screens.worlds.recordings import BASS, OTHER_RECONSTRUCTION, SONG, SONG_SAMPLE


class TestNothingOpenAtEveryDoor:
    """With nothing open, every door that loads loads at once, and Close is unavailable."""

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a project with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_each_door_loads_at_once(self, screen: Screen) -> None:
        """The browser, the Open menu, a voice and a conversion each load at once and the title follows."""
        reconstructions = screen.reconstructions
        empty = titled(screen, SONG.stem)

        def close_it_again(screen: Screen) -> None:
            reconstructions.close_from_menu()
            expect_title(screen, empty)

        def close_has_nothing_to_close(screen: Screen) -> None:
            assert not reconstructions.can_close()

            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)

            nothing_asked(screen)
            assert screen.title() == empty

        def the_browser_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            close_it_again(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OTHER_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            close_it_again(screen)

        def a_voice_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_SAMPLE)

            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False))
            nothing_asked(screen)
            close_it_again(screen)

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, SONG.stem, converted(home_path(BASS)).name))
            nothing_asked(screen)

        screen.scenario(
            close_has_nothing_to_close,
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            a_voice_opens_at_once,
            the_conversion_loads_at_once,
        ).run()

    def test_the_window_closes_at_once(self, screen: Screen) -> None:
        """Closing the window leaves the application at once."""
        screen.expect(screen.title, titled(screen, SONG.stem).__eq__, description="the song open")

        knock(screen, Door.WINDOW_CLOSE, voice=SONG_SAMPLE)

        assert screen.wait_for_exit()
