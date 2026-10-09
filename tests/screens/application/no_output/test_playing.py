import operator
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.steps.sequencer import on_the_sequencer
from automation.vocabulary.playback import PLAY
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, sequencer_world

NO_OUTPUT_TITLE: Final[str] = "global.dialog.title.no_audio_output"
NO_OUTPUT_MESSAGE: Final[str] = "global.dialog.message.no_audio_output"
MIDDLE_OF_THE_WAVEFORM: Final[float] = 0.5


@pytest.fixture
def world() -> World:
    """A home holding reconstructions that play and an arranged project."""
    return sequencer_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on a reconstruction that plays and on the arranged project."""
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)


def the_reader_is_told(screen: Screen) -> None:
    """Waits for the notice that no sound can play, reads its words, and dismisses it with OK.

    The Playback menu still offers Play, since nothing took the output.
    """
    notice = screen.no_output_notice
    screen.expect(notice.is_shown, bool, description="the notice that no sound can play")

    assert notice.prompt.title() == screen.words(NO_OUTPUT_TITLE)
    assert notice.words() == screen.words(NO_OUTPUT_MESSAGE)
    assert not screen.error_notice.is_shown()
    assert screen.sequencer.playback.play_entry() == screen.words(PLAY)

    notice.dismiss()
    screen.expect(notice.is_shown, operator.not_, description="the notice dismissed")


class TestPlayingAReconstruction:
    """With no output device, playing the open reconstruction tells the reader that no sound can play.

    Play brings up the notice with its words and leaves the Playback menu offering Play. Once OK
    dismisses it, a click on the waveform, which plays from there, brings the same notice up again.
    """

    def test_play_and_a_click_tell_the_reader(self, screen: Screen) -> None:
        """Each gesture brings up the plain notice, and no error is reported."""

        def play_tells_the_reader(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

            screen.press_shortcut(ShortcutId.PLAY)

            the_reader_is_told(screen)

        def a_click_on_the_waveform_tells_the_reader_again(screen: Screen) -> None:
            screen.reconstructions.waveform.click(MIDDLE_OF_THE_WAVEFORM)

            the_reader_is_told(screen)

        screen.scenario(play_tells_the_reader, a_click_on_the_waveform_tells_the_reader_again).run()


class TestPlayingTheSong:
    """With no output device, playing the open project's song tells the reader that no sound can play.

    Play on the Sequencer brings up the notice with its words and leaves the Playback menu offering
    Play. Once OK dismisses it, Play from this frame brings the same notice up again.
    """

    def test_play_and_play_from_this_frame_tell_the_reader(self, screen: Screen) -> None:
        """Each gesture brings up the plain notice, and no error is reported."""

        def play_tells_the_reader(screen: Screen) -> None:
            on_the_sequencer(screen)

            screen.press_shortcut(ShortcutId.PLAY)

            the_reader_is_told(screen)

        def play_from_this_frame_tells_the_reader_again(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY_FROM_FRAME)

            the_reader_is_told(screen)

        screen.scenario(play_tells_the_reader, play_from_this_frame_tells_the_reader_again).run()
