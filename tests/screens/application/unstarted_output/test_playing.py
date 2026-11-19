import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.output import the_reader_is_told_no_sound_plays
from automation.steps.reconstructions import expect_open
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, sequencer_world


@pytest.fixture
def world() -> World:
    """A home holding reconstructions that play and an arranged project."""
    return sequencer_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on a reconstruction that plays and on the arranged project."""
    return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=ARRANGED_PROJECT)


class TestPlayingWhereTheAudioSystemRefusedToStart:
    """Where the audio system refuses to start, the application opens as it does on a machine with no output.

    Both documents open, and playing the reconstruction brings up the notice that no sound can play,
    with no error reported.
    """

    def test_play_tells_the_reader(self, screen: Screen) -> None:
        """Play brings up the plain notice."""

        def play_tells_the_reader(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            expect_open(screen, PLAYABLE_RECONSTRUCTION)

            screen.press_shortcut(ShortcutId.PLAY)

            the_reader_is_told_no_sound_plays(screen)

        screen.scenario(play_tells_the_reader).run()
