from functools import partial
from typing import Final, List

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.tracker.constants import TYPING_FRAMES
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import (
    channels_sounding,
    leave_letting_the_project_go,
    on_the_sequencer,
    sounding_but,
)
from tests.suite.screens.worlds.songs import PAD_ROW

CARET_ROW: Final[int] = PAD_ROW + 1
TOGGLE_PULSE_TWO: Final[ShortcutId] = ShortcutId.TOGGLE_CHANNEL_PULSE_2


class TestTheChannelKeysBesideTheNotes:
    """With the cursor in a pitch column, Pulse 2's key types the note it names, and its chord mutes Pulse 2
    all the same.

    The key types a note on the Pad row, which moves the caret a row down, and the mix stays whole. The chord
    then mutes Pulse 2 and types nothing on the caret's row, and the chord again brings it back. The key
    pressed once more types a note on that row, which is where a chord that typed would have written.
    """

    def test_the_key_types_a_note_and_the_chord_mutes_pulse_two(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        caret_row: List[str] = []

        def caret_row_label() -> str:
            return tracker.label(CARET_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE)

        def the_key_types_a_note(screen: Screen) -> None:
            on_the_sequencer(screen)
            before = tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE)
            tracker.click(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE)

            screen.press_shortcut(TOGGLE_PULSE_TWO)

            screen.frames(TYPING_FRAMES)
            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) != before
            assert channels_sounding(screen) == sounding_but()
            caret_row.append(caret_row_label())

        def the_chord_mutes_pulse_two_and_types_nothing(screen: Screen) -> None:
            screen.press_shortcut_alias(TOGGLE_PULSE_TWO)

            screen.expect(
                partial(channels_sounding, screen),
                sounding_but(ChannelName.PULSE2).__eq__,
                description="Pulse 2 muted",
            )
            screen.frames(TYPING_FRAMES)
            assert caret_row_label() == caret_row[0]

        def the_chord_brings_it_back(screen: Screen) -> None:
            screen.press_shortcut_alias(TOGGLE_PULSE_TWO)

            screen.expect(
                partial(channels_sounding, screen),
                sounding_but().__eq__,
                description="every channel sounding again",
            )

        def the_key_types_on_the_caret_row(screen: Screen) -> None:
            screen.press_shortcut(TOGGLE_PULSE_TWO)

            screen.expect(caret_row_label, caret_row[0].__ne__, description="a note typed on the caret's row")
            assert channels_sounding(screen) == sounding_but()

        screen.scenario(
            the_key_types_a_note,
            the_chord_mutes_pulse_two_and_types_nothing,
            the_chord_brings_it_back,
            the_key_types_on_the_caret_row,
            leave_letting_the_project_go,
        ).run()
