import operator
from typing import Callable, Final

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.main import home_path
from automation.steps.project import leave_letting_the_project_go
from automation.steps.reconstructions import converted, edit_envelope, marked, titled, voice_title
from automation.steps.sequencer import open_voice
from automation.vocabulary.dialogs import EXIT_PROJECT_MESSAGE
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.prompts.every_door.cases import Door
from tests.screens.prompts.every_door.constants import SAMPLE_ORDINAL, SETTLING_FRAMES
from tests.screens.prompts.every_door.steps import expect_title, knock, nothing_asked
from tests.suite.screens.worlds.recordings import BASS, OTHER_RECONSTRUCTION, SONG, SONG_INSTRUMENT, SONG_SAMPLE

FADING: Final[str] = "12 8 4"


class TestAnInstrumentAtEveryDoor:
    """An instrument is put away at every door with no question, Close is unavailable, and the exit asks about
    the project.

    The instrument is opened and its volume envelope edited. The browser, the Open menu, a sample and a
    conversion each go through at once, and the edited instrument is still there when it is opened again.
    Close does nothing, and the exit and the window close ask about the project.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a project with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_no_door_asks_and_close_stands_aside(self, screen: Screen) -> None:
        """The doors go through at once, Close is unavailable and the exits ask about the project."""
        reconstructions = screen.reconstructions
        edited = titled(screen, marked(SONG.stem, unsaved=True))

        def open_the_instrument(screen: Screen) -> None:
            open_voice(screen, SONG_INSTRUMENT)
            screen.expect(reconstructions.instruments.offers_audition, bool, description="the instrument open")
            screen.expect(
                lambda: reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                FADING.__eq__,
                description="its edit drawn",
            )

        def edit_the_instrument(screen: Screen) -> None:
            open_voice(screen, SONG_INSTRUMENT)
            screen.expect(reconstructions.instruments.offers_audition, bool, description="the instrument open")

            edit_envelope(screen, channel=ChannelName.PULSE1, feature=FeatureKey.VOLUME, sequence=FADING, title=edited)

        def the_browser_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            assert not reconstructions.instruments.offers_audition()
            nothing_asked(screen)
            open_the_instrument(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OTHER_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            open_the_instrument(screen)

        def a_sample_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_SAMPLE)

            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=True))
            assert not reconstructions.instruments.offers_audition()
            nothing_asked(screen)
            open_the_instrument(screen)

        def close_has_nothing_to_close(screen: Screen) -> None:
            assert not reconstructions.can_close()

            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)

            nothing_asked(screen)
            assert reconstructions.instruments.offers_audition()
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == FADING
            assert screen.title() == edited

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), converted(home_path(BASS)).name))
            nothing_asked(screen)
            open_the_instrument(screen)

        def leaving_asks_about_the_project(door: Door) -> Callable[[Screen], None]:
            def step(screen: Screen) -> None:
                prompt = screen.project.unsaved_prompt

                knock(screen, door, voice=SONG_SAMPLE)

                screen.expect(prompt.is_shown, bool, description="the question about the project")
                assert prompt.words() == screen.words(EXIT_PROJECT_MESSAGE)
                prompt.cancel()
                screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
                screen.frames(SETTLING_FRAMES)
                assert reconstructions.instruments.offers_audition()

            step.__name__ = f"{door.value}_asks_about_the_project"
            return step

        screen.scenario(
            edit_the_instrument,
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            a_sample_opens_at_once,
            close_has_nothing_to_close,
            the_conversion_loads_at_once,
            leaving_asks_about_the_project(Door.EXIT),
            leaving_asks_about_the_project(Door.WINDOW_CLOSE),
            leave_letting_the_project_go,
        ).run()
