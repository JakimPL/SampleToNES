from functools import partial

from automation.dearpygui.items.types import Item
from automation.screen import Screen
from automation.vocabulary.playback import PLAY_VOICE
from sampletones_application.categories.hierarchy import Tab
from tests.suite.screens.worlds.songs import LINE


def voice_row(screen: Screen, name: str) -> Item:
    """Brings the Sequencer tab to the front and returns the list row of the voice called ``name``."""
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    return screen.expect_item(partial(screen.sequencer.voices.row, name), description=f"the row of {name}")


class TestPlayingASampleFromItsRow:
    """Play on a sample's row sounds the sample once its render lands, and the window answers meanwhile.

    A sample never opened on the Reconstructions tab has no render kept, so the preview is rendered
    on a worker of its own; the sound is heard once it lands, and the frames in between are drawn.
    """

    def test_play_sounds_the_sample_once_it_lands(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        menu = screen.context_menu
        heard = screen.sound_heard()

        voices.right_click(voice_row(screen, LINE))
        screen.expect(menu.is_shown, bool, description="the row's menu")
        menu.choose(screen.words(PLAY_VOICE))

        screen.expect(screen.sound_settled, bool, description="the preview landed")
        screen.expect(screen.sound_heard, heard.__lt__, description="the sample heard")
