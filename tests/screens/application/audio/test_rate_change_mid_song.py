import operator
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.vocabulary.playback import PAUSE, PLAY
from automation.worlds.home import World
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.application.audio.steps import play_the_looping_song, play_the_song
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, sequencer_world

CHOSEN_RATE: Final[int] = 48000
RATE_LABEL: Final[str] = "settings.audio.template.sample_rate_label"


@pytest.fixture
def world() -> World:
    """A home holding a project with a song to play."""
    return sequencer_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on the project with the song."""
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


class TestARateChangeMidSong:
    """A rate applied in Audio settings while the song plays stops the song, and the next Play plays at it.

    The song loops, so it plays until something ends it, on a stream at the device's own rate. Audio settings
    opens, another rate is picked and applied: the song stops without an error, its stream closed. Play then
    opens a stream at the rate applied, and the song is heard on it.
    """

    def test_the_song_stops_and_plays_again_at_the_rate_applied(self, screen: Screen) -> None:
        settings = screen.audio_settings
        chosen = screen.words(RATE_LABEL).format(rate=CHOSEN_RATE)

        def play_at_the_devices_rate(screen: Screen) -> None:
            play_the_looping_song(screen)

            assert screen.output_streams()[0].rate != CHOSEN_RATE

        def apply_another_rate(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.AUDIO_SETTINGS)
            screen.expect(settings.is_shown, bool, description="Audio settings")
            assert settings.sample_rate() != chosen

            settings.choose_sample_rate(chosen)
            assert screen.sequencer.playback.play_entry() == screen.words(PAUSE)
            settings.apply()

            screen.expect(settings.is_shown, operator.not_, description="Audio settings closed")
            screen.expect(screen.sequencer.playback.play_entry, screen.words(PLAY).__eq__, description="song stopped")
            screen.expect(lambda: screen.output_streams()[0].closed, bool, description="the song's stream closed")
            assert not screen.error_notice.is_shown()

        def play_at_the_rate_applied(screen: Screen) -> None:
            heard = screen.sound_heard()

            play_the_song(screen)

            screen.expect(lambda: len(screen.output_streams()), (2).__eq__, description="a second stream")
            assert screen.output_streams()[1].rate == CHOSEN_RATE
            screen.expect(screen.sound_heard, heard.__lt__, description="the song heard again")

        screen.scenario(play_at_the_devices_rate, apply_another_rate, play_at_the_rate_applied).run()
