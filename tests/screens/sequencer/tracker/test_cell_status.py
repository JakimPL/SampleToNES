from typing import Final

from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go, on_the_sequencer
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_voice_label
from tests.screens.sequencer.tracker.constants import LINE_NUMBER, PIANO_C, SAMPLE_COLUMN, TYPING_FRAMES
from tests.screens.sequencer.tracker.steps import play_a_note, type_into
from tests.suite.screens.worlds.songs import LINE, PAD, PAD_ROW

STATUS_VOICE: Final[str] = "sequencer.tracker.template.status_voice"
STATUS_SAMPLE: Final[str] = "sequencer.tracker.template.status_sample"
STATUS_NOTE: Final[str] = "sequencer.tracker.template.status_note"
STATUS_TRANSPOSE: Final[str] = "sequencer.tracker.template.status_transpose"
STATUS_VOLUME: Final[str] = "sequencer.tracker.template.status_volume"
STATUS_PITCH: Final[str] = "sequencer.tracker.label.status_pitch"
STATUS_DIFFERENT_PITCHES: Final[str] = "sequencer.tracker.label.status_different_pitches"
PAD_POSITION: Final[int] = 2
LINE_POSITION: Final[int] = 0
LINE_ROW: Final[int] = 0
EMPTY_ROW: Final[int] = 2
SAMPLE_ROW: Final[int] = 5
STEP_TYPED: Final[str] = "03"
STEP_SAID: Final[str] = "+3"
VOLUME_TYPED: Final[str] = "D"
VOLUME_SAID: Final[int] = 13
C_AT_OCTAVE_TWO: Final[str] = "C-2"


class TestHoveringASlot:
    """The status line says what the slot under the pointer holds: a voice by its number and name, a pitch
    by the face it was typed in, a volume by its level and an empty slot by its name. A Sample column slot
    whose channels differ says so, and the line clears once the pointer leaves the grid.
    """

    def test_the_status_names_the_slot(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def says(expected: str) -> None:
            screen.expect(screen.status, expected.__eq__, description=f"the status reading '{expected}'")

        def a_voice_and_a_step(screen: Screen) -> None:
            on_the_sequencer(screen)
            type_into(screen, PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE, STEP_TYPED)

            tracker.hover(PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)
            says(screen.words(STATUS_VOICE).format(voice=display_voice_label(PAD_POSITION, PAD)))

            tracker.hover(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE)
            says(screen.words(STATUS_TRANSPOSE).format(step=STEP_SAID))

        def a_note_and_a_volume(screen: Screen) -> None:
            play_a_note(screen, LINE_ROW, ChannelName.PULSE1, PIANO_C)
            type_into(screen, LINE_ROW, ChannelName.PULSE1, SubColumn.VOLUME, VOLUME_TYPED)

            tracker.hover(LINE_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE)
            says(screen.words(STATUS_NOTE).format(note=C_AT_OCTAVE_TWO))

            tracker.hover(LINE_ROW, ChannelName.PULSE1, SubColumn.VOLUME)
            says(screen.words(STATUS_VOLUME).format(volume=VOLUME_SAID))

        def an_empty_slot_names_itself(screen: Screen) -> None:
            tracker.hover(EMPTY_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE)

            says(screen.words(STATUS_PITCH))

        def the_sample_column_says_when_its_channels_differ(screen: Screen) -> None:
            type_into(screen, SAMPLE_ROW, SAMPLE_COLUMN, SubColumn.VOICE, LINE_NUMBER)
            tracker.click(SAMPLE_ROW, SAMPLE_COLUMN, SubColumn.TRANSPOSE)
            screen.hand.press_key(PIANO_C, modifiers=[])
            screen.frames(TYPING_FRAMES)

            tracker.hover(SAMPLE_ROW, SAMPLE_COLUMN, SubColumn.VOICE)
            says(screen.words(STATUS_SAMPLE).format(voice=display_voice_label(LINE_POSITION, LINE)))

            tracker.hover(SAMPLE_ROW, SAMPLE_COLUMN, SubColumn.TRANSPOSE)
            says(screen.words(STATUS_DIFFERENT_PITCHES))

        def leaving_the_grid_clears_the_line(screen: Screen) -> None:
            tracker.leave()

            says("")

        screen.scenario(
            a_voice_and_a_step,
            a_note_and_a_volume,
            an_empty_slot_names_itself,
            the_sample_column_says_when_its_channels_differ,
            leaving_the_grid_clears_the_line,
            leave_letting_the_project_go,
        ).run()
