from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.sequencer.tracker.band.constants import CHANNEL, SLOT
from tests.suite.screens.screen import Screen
from tests.suite.screens.vocabulary.playback import PAUSE, RESUME


def expect_centered(screen: Screen, row: int) -> None:
    """Waits until ``row`` of the shown frame stands at the middle of the tracker's band."""
    screen.expect(
        screen.sequencer.tracker.centered_row,
        row.__eq__,
        description=f"row {row} at the band's center",
    )


def show_frame(screen: Screen, frame: int) -> None:
    """Shows ``frame`` in the tracker from the Order grid, then hands the keys back to the tracker's first row."""
    screen.sequencer.order.click(CHANNEL, frame)
    screen.sequencer.tracker.click(0, CHANNEL, SLOT)
    screen.expect(
        lambda: screen.sequencer.tracker.has_caret(0, CHANNEL),
        bool,
        description="the caret on the frame's first row",
    )


def press(screen: Screen, shortcut_id: ShortcutId, times: int) -> None:
    """Presses the keys the scheme gives ``shortcut_id`` ``times`` times over."""
    for _ in range(times):
        screen.press_shortcut(shortcut_id)


def expect_playing(screen: Screen) -> None:
    """Waits until the Playback menu offers to pause, which it does while the song plays."""
    playback = screen.sequencer.playback
    screen.expect(playback.play_entry, screen.words(PAUSE).__eq__, description="the song playing")


def expect_paused(screen: Screen) -> None:
    """Waits until the Playback menu offers to resume, which it does while the song stands paused."""
    playback = screen.sequencer.playback
    screen.expect(playback.play_entry, screen.words(RESUME).__eq__, description="the song paused")


def expect_stopped(screen: Screen) -> None:
    """Waits until Stop no longer answers, which a stopped song reads as."""
    playback = screen.sequencer.playback
    screen.expect(lambda: not playback.can_stop(), bool, description="the song stopped")
