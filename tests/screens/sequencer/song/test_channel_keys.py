from functools import partial
from typing import Final, List

from automation.screen import Screen
from automation.steps.sequencer import (
    channels_sounding,
    on_the_sequencer,
    sounding_but,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.song.constants import SETTLING_FRAMES

FIRST_POSITION: Final[int] = 0
TOGGLE_PULSE_TWO: Final[ShortcutId] = ShortcutId.TOGGLE_CHANNEL_PULSE_2


class TestTheChannelKeysBesideTheOrder:
    """With the cursor on an order entry, Pulse 2's chord mutes Pulse 2 and types nothing, while its key types
    a digit.

    The chord mutes Pulse 2 and leaves the entry as it read, and the chord again brings it back. The key then
    types its digit into the same entry, which is what a chord that typed would have shown.
    """

    def test_the_chord_mutes_pulse_two_and_the_key_types(self, screen: Screen) -> None:
        order = screen.sequencer.order
        entry: List[str] = []

        def entry_label() -> str:
            return order.label(ChannelName.PULSE2, FIRST_POSITION)

        def the_chord_mutes_pulse_two_and_types_nothing(screen: Screen) -> None:
            on_the_sequencer(screen)
            entry.append(entry_label())
            order.click(ChannelName.PULSE2, FIRST_POSITION)

            screen.press_shortcut_alias(TOGGLE_PULSE_TWO)

            screen.expect(
                partial(channels_sounding, screen),
                sounding_but(ChannelName.PULSE2).__eq__,
                description="Pulse 2 muted",
            )
            screen.frames(SETTLING_FRAMES)
            assert entry_label() == entry[0]

        def the_chord_brings_it_back(screen: Screen) -> None:
            screen.press_shortcut_alias(TOGGLE_PULSE_TWO)

            screen.expect(
                partial(channels_sounding, screen),
                sounding_but().__eq__,
                description="every channel sounding again",
            )

        def the_key_types_into_the_entry(screen: Screen) -> None:
            screen.press_shortcut(TOGGLE_PULSE_TWO)

            screen.expect(entry_label, entry[0].__ne__, description="a digit typed into the entry")
            assert channels_sounding(screen) == sounding_but()

        screen.scenario(
            the_chord_mutes_pulse_two_and_types_nothing,
            the_chord_brings_it_back,
            the_key_types_into_the_entry,
        ).run()
