import operator
from typing import Dict, Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.reconstructions.player.constants import RECONSTRUCTION_LINE
from tests.screens.reconstructions.player.steps import advancing, entry, expect_entry
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import expect_open, load_from_the_browser
from tests.suite.screens.vocabulary.playback import PAUSE, PLAY
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION, SECOND_PLAYABLE

BEAT_FRAMES: Final[int] = 15
BEAT_LENGTH: Final[int] = 3
SILENCE: Final[float] = 1e-6
SILENT_SHARE_TOLERANCE: Final[float] = 0.05


def silent_share(drawn: List[float]) -> float:
    """The share of drawn heights that sit at silence."""
    return sum(1 for height in drawn if abs(height) < SILENCE) / len(drawn)


class TestPlayingFromTheBrowser:
    """A reconstruction opened from the browser plays on Space, its cursor moving along the waveform."""

    def test_space_plays_and_the_cursor_moves_on(self, screen: Screen) -> None:
        """The reconstruction opens stopped, and Space starts it with the cursor moving along the waveform."""
        waveform = screen.reconstructions.waveform

        def open_it(screen: Screen) -> None:
            load_from_the_browser(screen, PLAYABLE_RECONSTRUCTION)

            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            assert waveform.cursor() is None
            assert entry(screen) == screen.words(PLAY)

        def space_plays_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, PAUSE)
            first = screen.expect(waveform.cursor, bool, description="the cursor")
            assert first is not None
            advancing(screen, waveform, first)

        screen.scenario(open_it, space_plays_it).run()


class TestAnotherReconstructionAfterClosing:
    """A reconstruction opened after another was closed draws its cursor as it plays.

    The first reconstruction plays, stops and closes from the menu; the second opens from the browser, plays,
    and its cursor moves on.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_its_cursor_moves_on(self, screen: Screen) -> None:
        """The second reconstruction plays with its cursor advancing."""
        reconstructions = screen.reconstructions
        waveform = reconstructions.waveform

        def play_and_close_the_first(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.press_shortcut(ShortcutId.PLAY)
            expect_entry(screen, PAUSE)
            screen.press_shortcut(ShortcutId.STOP)
            expect_entry(screen, PLAY)

            reconstructions.close_from_menu()

            screen.expect(reconstructions.file_line, operator.not_, description="nothing open")

        def open_the_second_and_play(screen: Screen) -> None:
            load_from_the_browser(screen, SECOND_PLAYABLE)
            expect_open(screen, SECOND_PLAYABLE)

            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, PAUSE)
            first = screen.expect(waveform.cursor, bool, description="the cursor")
            assert first is not None
            advancing(screen, waveform, first)
            screen.press_shortcut(ShortcutId.STOP)
            expect_entry(screen, PLAY)

        screen.scenario(play_and_close_the_first, open_the_second_and_play).run()


class TestChoosingChannels:
    """The waveform draws the channels ticked above it, and ticking one back draws what it drew before.

    The scenario unticks Pulse 1 and Triangle, which leaves the beat alone, and ticks them again.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_the_beat_alone_falls_silent_between_its_strokes(self, screen: Screen) -> None:
        """The beat alone is silent between its strokes; ticking the channels back restores the drawing."""
        reconstructions = screen.reconstructions
        waveform = reconstructions.waveform
        line = screen.words(RECONSTRUCTION_LINE)
        drawn: Dict[str, List[float]] = {}

        def every_channel_sounds_throughout(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            drawn["all"] = waveform.drawn(line)

            assert silent_share(drawn["all"]) == 0.0

        def the_beat_alone(screen: Screen) -> None:
            for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
                reconstructions.tick_channel(channel)

            beat = screen.expect(
                lambda: waveform.drawn(line),
                drawn["all"].__ne__,
                description="the waveform redrawn",
            )
            assert abs(silent_share(beat) - (BEAT_FRAMES - BEAT_LENGTH) / BEAT_FRAMES) <= SILENT_SHARE_TOLERANCE

        def every_channel_back(screen: Screen) -> None:
            for channel in (ChannelName.PULSE1, ChannelName.TRIANGLE):
                reconstructions.tick_channel(channel)

            screen.expect(lambda: waveform.drawn(line), drawn["all"].__eq__, description="the waveform as before")

        screen.scenario(every_channel_sounds_throughout, the_beat_alone, every_channel_back).run()
