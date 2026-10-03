from typing import Final, List, Optional, Tuple

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import BLANK
from tests.screens.sequencer.song.constants import EMPTY_VOICE, SETTLING_FRAMES
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer

EVERY_CHANNEL: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())
SAMPLE_COLUMN: Final[Optional[ChannelName]] = None


class TestAVolumeWhereNoSamplePlays:
    """A volume typed in the Sample column of an empty frame keeps the cell blank, adds no history entry and
    creates no pattern.

    An empty second frame is added, a volume is typed on its first row, and the scenario expects the cell,
    the history and the order entries of that frame to stay as they were.
    """

    def test_the_frame_stays_empty(self, screen: Screen) -> None:
        """The frame stays empty after the volume is typed."""
        order = screen.sequencer.order
        tracker = screen.sequencer.tracker
        history = screen.sequencer.history
        before: List[int] = []

        def add_an_empty_frame(screen: Screen) -> None:
            on_the_sequencer(screen)
            order.click(ChannelName.PULSE1, 0)

            screen.press_shortcut(ShortcutId.ORDER_ADD_FRAME)

            screen.expect(order.positions, (2).__eq__, description="a second frame")
            assert [order.label(channel, 1) for channel in EVERY_CHANNEL] == [EMPTY_VOICE] * len(EVERY_CHANNEL)

        def type_a_volume_on_it(screen: Screen) -> None:
            order.click(ChannelName.PULSE1, 1)
            before.append(len(history.lines()))
            tracker.click(0, SAMPLE_COLUMN, SubColumn.VOLUME)

            screen.hand.type_text("5")

            screen.frames(SETTLING_FRAMES)
            assert tracker.label(0, SAMPLE_COLUMN, SubColumn.VOLUME) == BLANK
            assert len(history.lines()) == before[0]
            assert [order.label(channel, 1) for channel in EVERY_CHANNEL] == [EMPTY_VOICE] * len(EVERY_CHANNEL)

        screen.scenario(add_an_empty_frame, type_a_volume_on_it, leave_letting_the_project_go).run()
