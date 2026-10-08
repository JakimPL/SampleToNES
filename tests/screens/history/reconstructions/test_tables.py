from typing import Dict, Final, List, Tuple

from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go, open_voice
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.history.constants import LEAD
from tests.screens.history.steps import (
    Fields,
    expect_lines,
    expect_reading,
    history_count,
    leading,
    press_on_the_sequencer,
    typed_values,
    volume_fields,
)

TYPED: Final[Dict[ChannelName, str]] = {ChannelName.PULSE1: "9 7", ChannelName.PULSE2: "6"}
CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(TYPED)
NEWEST_LINE: Final[int] = 0


class TestVolumesTypedIntoTwoChannelsOfOneSample:
    """Volumes typed into two channels of one sample make one history entry, which every way back and forth reaches.

    Lead opens from its row's menu, and a volume sequence is typed into Pulse 1 and then into Pulse 2: the
    History card gains one line. Undo on the Sequencer brings both fields back to what they read, and Redo
    brings both typed sequences back. Clicking the oldest line and then the newest does the same.
    """

    def test_one_entry_reached_every_way(self, screen: Screen) -> None:
        instruments = screen.reconstructions.instruments
        history = screen.sequencer.history
        readings: List[Fields] = []
        lines: List[int] = []

        def type_into_both_channels(screen: Screen) -> None:
            open_voice(screen, LEAD)
            screen.expect(screen.tabs.front, Tab.RECONSTRUCTIONS.__eq__, description="Lead open")
            readings.append(volume_fields(screen, CHANNELS))
            lines.append(history_count(screen))

            for channel, sequence in TYPED.items():
                instruments.type_envelope(channel, FeatureKey.VOLUME, sequence)
                screen.expect(
                    lambda: instruments.envelope(channel, FeatureKey.VOLUME),
                    lambda text: text != readings[0][channel],
                    description=f"{channel} typed",
                )

            expect_lines(screen, lines[0] + 1)

        def undo_takes_back_both(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.UNDO)

            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), readings[0], "both channels as they stood")
            assert history_count(screen) == lines[0] + 1

        def redo_brings_back_both(screen: Screen) -> None:
            press_on_the_sequencer(screen, ShortcutId.REDO)

            expect_reading(
                screen,
                lambda: leading(volume_fields(screen, CHANNELS), TYPED),
                typed_values(TYPED),
                "both channels as typed",
            )
            readings.append(volume_fields(screen, CHANNELS))

        def the_oldest_and_the_newest_line(screen: Screen) -> None:
            history.jump_to(history_count(screen) - 1)
            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), readings[0], "the oldest line's state")

            history.jump_to(NEWEST_LINE)

            expect_reading(screen, lambda: volume_fields(screen, CHANNELS), readings[1], "the newest line's state")

        screen.scenario(
            type_into_both_channels,
            undo_takes_back_both,
            redo_brings_back_both,
            the_oldest_and_the_newest_line,
            leave_letting_the_project_go,
        ).run()
