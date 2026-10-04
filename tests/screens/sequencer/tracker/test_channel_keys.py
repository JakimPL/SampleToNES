from functools import partial
from typing import Final, List

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.tracker.constants import TYPING_FRAMES
from tests.screens.sequencer.tracker.steps import play_a_note
from tests.suite.screens.dearpygui.keys import IMGUI_DIGIT_ZERO, IMGUI_LEFT_ALT
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import channels_sounding, leave_letting_the_project_go, on_the_sequencer
from tests.suite.screens.worlds.songs import PAD_ROW

DIGIT_TWO: Final[int] = IMGUI_DIGIT_ZERO + 2
EVERY_CHANNEL_SOUNDING: Final[List[bool]] = [True, True, True, True]
PULSE_TWO_MUTED: Final[List[bool]] = [True, False, True, True]


class TestTheChannelKeysBesideTheNotes:
    """With the cursor in a pitch column, 2 types the note it names, and Alt+2 mutes Pulse 2 all the same.

    A note is typed with 2 and the mix stays whole. Alt+2 then mutes Pulse 2 and leaves the note, and Alt+2
    again brings it back.
    """

    def test_two_types_a_note_and_alt_two_mutes_pulse_two(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        typed: List[str] = []

        def two_types_a_note(screen: Screen) -> None:
            on_the_sequencer(screen)
            before = tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE)

            play_a_note(screen, PAD_ROW, ChannelName.PULSE2, DIGIT_TWO)

            typed.append(tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE))
            assert typed[0] != before
            assert channels_sounding(screen) == EVERY_CHANNEL_SOUNDING

        def alt_two_mutes_pulse_two(screen: Screen) -> None:
            screen.hand.press_key(DIGIT_TWO, modifiers=[IMGUI_LEFT_ALT])

            screen.expect(partial(channels_sounding, screen), PULSE_TWO_MUTED.__eq__, description="Pulse 2 muted")
            screen.frames(TYPING_FRAMES)
            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == typed[0]

        def alt_two_brings_it_back(screen: Screen) -> None:
            screen.hand.press_key(DIGIT_TWO, modifiers=[IMGUI_LEFT_ALT])

            screen.expect(
                partial(channels_sounding, screen),
                EVERY_CHANNEL_SOUNDING.__eq__,
                description="every channel sounding again",
            )

        screen.scenario(
            two_types_a_note,
            alt_two_mutes_pulse_two,
            alt_two_brings_it_back,
            leave_letting_the_project_go,
        ).run()
