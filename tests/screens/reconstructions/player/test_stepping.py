import operator
from typing import Final, List

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.vocabulary.playback import PAUSE, PLAY
from sampletones_application.tags.general import TAG_GLOBAL_MENU_ITEM_PLAYBACK_STEP_FORWARD
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.reconstructions import Reconstruction
from tests.screens.reconstructions.player.constants import STILL_FRAMES
from tests.screens.reconstructions.player.steps import entry, expect_entry, held_still
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION

RESUME: Final[str] = "global.menu.label.item_playback_resume"


class TestStepping:
    """Step forward and Step back move the paused playhead from frame boundary to frame boundary, a step while
    playing pauses first, and a step with nothing playing moves nothing.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """A reconstruction is open at start, with no project."""
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_steps_walk_the_paused_playhead_frame_by_frame(self, screen: Screen) -> None:
        """Each step lands on a frame boundary one frame from the last, and the playback stays paused."""
        waveform = screen.reconstructions.waveform
        ticks: List[int] = []
        stood: List[float] = []

        def expect_cursor_at(sample: float) -> None:
            screen.expect(waveform.cursor, float(sample).__eq__, description=f"the cursor at sample {sample:.0f}")

        def a_step_with_nothing_playing_moves_nothing(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            ticks.append(Reconstruction.load(PLAYABLE_RECONSTRUCTION).config.frame_length)

            screen.press_shortcut(ShortcutId.STEP_FORWARD)

            screen.frames(STILL_FRAMES)
            assert waveform.cursor() is None
            assert entry(screen) == screen.words(PLAY)
            assert not screen.menu.is_tagged_enabled(TAG_GLOBAL_MENU_ITEM_PLAYBACK_STEP_FORWARD)

        def pause_partway(screen: Screen) -> None:
            waveform.click(0.5)
            expect_entry(screen, PAUSE)
            screen.press_shortcut(ShortcutId.PLAY)

            expect_entry(screen, RESUME)
            screen.frames(STILL_FRAMES)
            stood.append(held_still(screen, waveform))
            assert screen.menu.is_tagged_enabled(TAG_GLOBAL_MENU_ITEM_PLAYBACK_STEP_FORWARD)

        def a_step_forward_lands_on_the_next_boundary(screen: Screen) -> None:
            tick = ticks[0]

            screen.press_shortcut(ShortcutId.STEP_FORWARD)

            expect_cursor_at((int(stood[0]) // tick + 1) * tick)
            assert entry(screen) == screen.words(RESUME)

        def each_step_moves_one_frame(screen: Screen) -> None:
            tick = ticks[0]
            boundary = (int(stood[0]) // tick + 1) * tick

            screen.press_shortcut(ShortcutId.STEP_FORWARD)
            expect_cursor_at(boundary + tick)
            screen.press_shortcut(ShortcutId.STEP_BACKWARD)
            screen.press_shortcut(ShortcutId.STEP_BACKWARD)

            expect_cursor_at(boundary - tick)
            assert held_still(screen, waveform) == boundary - tick

        def a_step_while_playing_pauses_on_a_boundary(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.PLAY)
            expect_entry(screen, PAUSE)

            screen.press_shortcut(ShortcutId.STEP_FORWARD)

            expect_entry(screen, RESUME)
            assert held_still(screen, waveform) % ticks[0] == 0

        def stop_takes_the_cursor_away(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.STOP)

            expect_entry(screen, PLAY)
            screen.expect(waveform.cursor, operator.not_, description="no cursor")

        screen.scenario(
            a_step_with_nothing_playing_moves_nothing,
            pause_partway,
            a_step_forward_lands_on_the_next_boundary,
            each_step_moves_one_frame,
            a_step_while_playing_pauses_on_a_boundary,
            stop_takes_the_cursor_away,
        ).run()
