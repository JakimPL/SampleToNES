import operator
from functools import partial
from typing import Callable, List

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.main import home_path
from automation.steps.project import leave_letting_the_project_go
from automation.steps.reconstructions import converted, marked, raise_the_first_level, titled, voice_title
from automation.steps.sequencer import open_voice
from automation.vocabulary.dialogs import EXIT_PROJECT_MESSAGE
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.prompts.every_door.cases import Door
from tests.screens.prompts.every_door.constants import SAMPLE_ORDINAL, SETTLING_FRAMES
from tests.screens.prompts.every_door.steps import expect_title, knock, nothing_asked
from tests.suite.screens.worlds.recordings import BASS, OTHER_RECONSTRUCTION, SONG, SONG_INSTRUMENT, SONG_SAMPLE


class TestAnEditedSampleAtEveryDoor:
    """An edited sample of the project is put away at every door with no question, and its edits stay in the
    project.

    The sample is opened and edited. The browser, the Open menu, another voice, Close and a conversion each
    go through at once, and the edited sample is still there when it is opened again. Only the exit and the
    window close ask, and they ask about the project.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a project with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_no_door_asks_and_the_exit_asks_about_the_project(self, screen: Screen) -> None:
        """The doors go through at once and the exits ask about the project."""
        reconstructions = screen.reconstructions
        edit: List[str] = []
        sample_open = partial(voice_title, screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=True)

        def open_the_sample(screen: Screen) -> None:
            open_voice(screen, SONG_SAMPLE)
            expect_title(screen, sample_open())
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == edit[0]

        def edit_the_sample(screen: Screen) -> None:
            open_voice(screen, SONG_SAMPLE)
            expect_title(screen, voice_title(screen, SONG.stem, SAMPLE_ORDINAL, SONG_SAMPLE, unsaved=False))

            edit.append(raise_the_first_level(screen, ChannelName.PULSE1, title=sample_open()))

        def the_browser_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.BROWSER, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            open_the_sample(screen)

        def the_menu_asks_for_a_file_at_once(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.OPEN, OTHER_RECONSTRUCTION)

            knock(screen, Door.MENU_OPEN, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), OTHER_RECONSTRUCTION.name))
            nothing_asked(screen)
            open_the_sample(screen)

        def another_voice_opens_at_once(screen: Screen) -> None:
            knock(screen, Door.VOICE_MENU, voice=SONG_INSTRUMENT)

            screen.expect(reconstructions.instruments.offers_audition, bool, description="the instrument open")
            assert screen.title() == titled(screen, marked(SONG.stem, unsaved=True))
            nothing_asked(screen)
            open_the_sample(screen)

        def close_closes_at_once(screen: Screen) -> None:
            knock(screen, Door.CLOSE, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True)))
            assert reconstructions.file_line() == ""
            nothing_asked(screen)
            open_the_sample(screen)

        def the_conversion_loads_at_once(screen: Screen) -> None:
            knock(screen, Door.CONVERSION_LOAD, voice=SONG_SAMPLE)

            expect_title(screen, titled(screen, marked(SONG.stem, unsaved=True), converted(home_path(BASS)).name))
            nothing_asked(screen)
            open_the_sample(screen)

        def leaving_asks_about_the_project(door: Door) -> Callable[[Screen], None]:
            def step(screen: Screen) -> None:
                prompt = screen.project.unsaved_prompt

                knock(screen, door, voice=SONG_SAMPLE)

                screen.expect(prompt.is_shown, bool, description="the question about the project")
                assert prompt.words() == screen.words(EXIT_PROJECT_MESSAGE)
                assert not reconstructions.unsaved_prompt.is_shown()
                prompt.cancel()
                screen.expect(prompt.is_shown, operator.not_, description="the question taken back")
                screen.frames(SETTLING_FRAMES)
                assert screen.title() == sample_open()

            step.__name__ = f"{door.value}_asks_about_the_project"
            return step

        screen.scenario(
            edit_the_sample,
            the_browser_loads_at_once,
            the_menu_asks_for_a_file_at_once,
            another_voice_opens_at_once,
            close_closes_at_once,
            the_conversion_loads_at_once,
            leaving_asks_about_the_project(Door.EXIT),
            leaving_asks_about_the_project(Door.WINDOW_CLOSE),
            leave_letting_the_project_go,
        ).run()
