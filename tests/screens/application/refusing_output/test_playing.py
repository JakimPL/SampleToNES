import operator

import pytest

from automation.application.startup import Startup
from automation.boundaries.audio import REFUSED_STREAM
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.vocabulary.playback import PLAY
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.application.refusing_output.constants import PLAYBACK_ERROR_MESSAGE
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION, playing_world


@pytest.fixture
def world() -> World:
    """A home holding reconstructions that play."""
    return playing_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on a reconstruction that plays."""
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)


class TestPlayingOnADeviceThatRefusesTheStream:
    """A stream the device refuses to open is reported as an error, and the application goes on answering.

    The device refuses on the thread that plays the audio, so the report crosses to the render thread
    before the error window opens. Play brings up the error with its words; once OK dismisses it, the
    Playback menu offers Play and a second Play reports the refusal again.
    """

    def test_play_reports_the_refusal_each_time(self, screen: Screen) -> None:
        notice = screen.error_notice

        def play_reports_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)

            screen.expect(notice.is_shown, bool, description="the error about the refused stream")
            screen.claim_error(REFUSED_STREAM)
            assert screen.words(PLAYBACK_ERROR_MESSAGE) in notice.words()

            notice.dismiss()

            screen.expect(notice.is_shown, operator.not_, description="the error dismissed")
            screen.expect(
                screen.sequencer.playback.play_entry,
                screen.words(PLAY).__eq__,
                description="the Playback menu offering Play",
            )

        def open_it(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

        screen.scenario(open_it, play_reports_it, play_reports_it).run()
