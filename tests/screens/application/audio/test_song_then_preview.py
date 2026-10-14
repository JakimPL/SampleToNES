from typing import List

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.sequencer import voice_row
from automation.vocabulary.playback import PLAY, PLAY_VOICE
from automation.worlds.home import World
from tests.screens.application.audio.steps import play_the_looping_song, play_the_song
from tests.suite.screens.worlds.songs import ARRANGED_PROJECT, LINE, sequencer_world


@pytest.fixture
def world() -> World:
    """A home holding a project with a song and a sample to preview."""
    return sequencer_world()


@pytest.fixture
def startup() -> Startup:
    """The application opens on the project with the song."""
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


class TestASongAPreviewAndLeaving:
    """The song, a preview taking the device from it, the song again, and leaving while it plays.

    The song loops, so it plays until something ends it, on a stream of its own. A voice played from its row
    takes the device: the song stops, and the preview plays on a stream of its own to its end. Play starts the
    song again on a third stream, and closing the window while it plays leaves at once, with every stream
    closed and the backend terminated.
    """

    def test_every_sound_plays_on_a_stream_of_its_own_and_leaving_closes_them(self, screen: Screen) -> None:
        heard: List[int] = []

        def play_the_song_on_a_loop(screen: Screen) -> None:
            play_the_looping_song(screen)

            screen.expect(screen.sound_heard, bool, description="the song heard")
            assert len(screen.output_streams()) == 1

        def preview_the_voice(screen: Screen) -> None:
            heard.append(screen.sound_heard())
            screen.sequencer.voices.right_click(voice_row(screen, LINE))
            screen.expect(screen.context_menu.is_shown, bool, description="the row's menu")
            screen.context_menu.choose(screen.words(PLAY_VOICE))

            screen.expect(lambda: len(screen.output_streams()), (2).__eq__, description="the preview's stream")
            screen.expect(screen.sequencer.playback.play_entry, screen.words(PLAY).__eq__, description="song stopped")
            assert screen.output_streams()[0].closed

        def the_preview_plays_to_its_end(screen: Screen) -> None:
            screen.expect(lambda: screen.output_streams()[1].closed, bool, description="the preview played out")

            assert screen.sound_heard() > heard[0]

        def play_the_song_again(screen: Screen) -> None:
            play_the_song(screen)

            screen.expect(lambda: len(screen.output_streams()), (3).__eq__, description="the song's second stream")

        def leave_while_it_plays(screen: Screen) -> None:
            assert not screen.output_streams()[2].closed

            screen.close_window()

            assert screen.wait_for_exit()
            assert all(stream.closed for stream in screen.output_streams())
            assert screen.backends_terminated() >= 1

        screen.scenario(
            play_the_song_on_a_loop,
            preview_the_voice,
            the_preview_plays_to_its_end,
            play_the_song_again,
            leave_while_it_plays,
        ).run()
