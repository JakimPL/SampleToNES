from typing import Dict, Final, FrozenSet, List, Mapping, Optional, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.notes import Note
from sampletones_tools.calibration.referee.search import (
    ASSIGNMENT,
    COLUMNS,
    DECODER,
    GAINS,
    MISPLACED,
    UNREACHED,
    SearchReferee,
    formable,
)
from sampletones_tools.calibration.trace import InstructionColumn, SearchTrace

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 4
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=11, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=9, duty_cycle=1)
FILLER: Final[PulseInstruction] = PulseInstruction(on=True, pitch=36, volume=15, duty_cycle=2)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=60)
BASS_ON_A_PULSE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=48, volume=15, duty_cycle=2)
SILENT_PULSE: Final[PulseInstruction] = PulseInstruction(on=False, pitch=64, volume=0, duty_cycle=2)
SILENT_TRIANGLE: Final[TriangleInstruction] = TriangleInstruction(on=False, pitch=60)
HISS: Final[NoiseInstruction] = NoiseInstruction(on=True, period=6, volume=10, short=False)

CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: HARMONY,
    ChannelName.TRIANGLE: BASS,
}
SILENCES: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: SILENT_PULSE,
    ChannelName.PULSE2: SILENT_PULSE,
    ChannelName.TRIANGLE: SILENT_TRIANGLE,
}


@pytest.fixture(name="referee")
def referee_fixture() -> SearchReferee:
    return SearchReferee()


def _held(frames: Mapping[ChannelName, InstructionUnion]) -> Dict[ChannelName, List[InstructionUnion]]:
    return {channel: [instruction] * FRAMES for channel, instruction in frames.items()}


def _trace(
    columns: Mapping[ChannelName, Sequence[InstructionUnion]],
    decoded: Mapping[ChannelName, InstructionUnion],
) -> SearchTrace:
    """A search offering the same column and decoding the same frame on every frame of each channel."""
    held: Dict[ChannelName, Tuple[InstructionColumn, ...]] = {
        channel: (tuple(column),) * FRAMES for channel, column in columns.items()
    }
    return SearchTrace(
        columns=held,
        decoded={channel: (instruction,) * FRAMES for channel, instruction in decoded.items()},
    )


def _judged(referee: SearchReferee, truth: Truth, trace: SearchTrace) -> Dict[str, float]:
    judgment = judged(referee.judge(truth, trace, converted(_held(CHORD))))
    return judgment.readings()


CHORD_TRUTH: Final[Truth] = written_truth(_held(CHORD))


class TestSearchReferee:
    def test_a_search_offering_and_decoding_the_written_notes_scores_zero(self, referee: SearchReferee) -> None:
        trace = _trace({channel: [frame, SILENCES[channel]] for channel, frame in CHORD.items()}, CHORD)

        readings = _judged(referee, CHORD_TRUTH, trace)

        assert readings["score"] == 0.0
        assert (readings[UNREACHED], readings[GAINS]) == (0.0, 0.0)

    def test_notes_no_column_offers_are_lost_at_the_columns(self, referee: SearchReferee) -> None:
        columns = {
            ChannelName.PULSE1: [LEAD, SILENT_PULSE],
            ChannelName.PULSE2: [FILLER, SILENT_PULSE],
            ChannelName.TRIANGLE: [SILENT_TRIANGLE],
        }
        decoded = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: FILLER, ChannelName.TRIANGLE: SILENT_TRIANGLE}

        readings = _judged(referee, CHORD_TRUTH, _trace(columns, decoded))

        assert (readings["score"], readings[COLUMNS]) == (1.0, 1.0)
        assert readings[UNREACHED] == pytest.approx(2 / 3)

    def test_columns_holding_the_notes_under_picks_that_miss_them_lose_them_at_the_assignment(
        self,
        referee: SearchReferee,
    ) -> None:
        columns = {
            ChannelName.PULSE1: [LEAD, SILENT_PULSE],
            ChannelName.PULSE2: [FILLER, HARMONY, SILENT_PULSE],
            ChannelName.TRIANGLE: [BASS, SILENT_TRIANGLE],
        }
        decoded = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: FILLER, ChannelName.TRIANGLE: BASS}

        readings = _judged(referee, CHORD_TRUTH, _trace(columns, decoded))

        assert (readings[COLUMNS], readings[ASSIGNMENT], readings[UNREACHED]) == (0.0, 1.0, 0.0)

    def test_picks_holding_the_notes_and_a_decoder_moving_off_them_lose_them_at_the_decoder(
        self,
        referee: SearchReferee,
    ) -> None:
        columns = {channel: [frame, SILENCES[channel]] for channel, frame in CHORD.items()}
        decoded = {**CHORD, ChannelName.TRIANGLE: SILENT_TRIANGLE}

        readings = _judged(referee, CHORD_TRUTH, _trace(columns, decoded))

        assert (readings["score"], readings[DECODER]) == (1.0, 1.0)

    def test_a_decoder_putting_wrong_picks_right_counts_as_a_gain(self, referee: SearchReferee) -> None:
        columns = {
            ChannelName.PULSE1: [LEAD, SILENT_PULSE],
            ChannelName.PULSE2: [HARMONY, SILENT_PULSE],
            ChannelName.TRIANGLE: [BASS, SILENT_TRIANGLE],
            ChannelName.NOISE: [HISS],
        }
        truth = written_truth(_held({ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}))
        decoded = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY, ChannelName.TRIANGLE: SILENT_TRIANGLE}

        readings = _judged(referee, truth, _trace(columns, decoded))

        assert (readings["score"], readings[GAINS]) == (0.0, 1.0)

    def test_a_bass_decoded_on_a_pulse_is_wrong_and_reads_as_misplaced(self, referee: SearchReferee) -> None:
        columns = {
            ChannelName.PULSE1: [LEAD, SILENT_PULSE],
            ChannelName.PULSE2: [BASS_ON_A_PULSE, HARMONY, SILENT_PULSE],
            ChannelName.TRIANGLE: [SILENT_TRIANGLE],
        }
        decoded = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: BASS_ON_A_PULSE, ChannelName.TRIANGLE: SILENT_TRIANGLE}
        truth = written_truth(_held({ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}))

        readings = _judged(referee, truth, _trace(columns, decoded))

        assert (readings["score"], readings[MISPLACED], readings[COLUMNS]) == (1.0, 1.0, 1.0)

    def test_frames_the_writing_leaves_silent_go_uncounted(self, referee: SearchReferee) -> None:
        rest: List[InstructionUnion] = [SILENT_PULSE] * FRAMES
        truth = written_truth({ChannelName.PULSE1: [LEAD] * FRAMES + rest})
        columns = {ChannelName.PULSE1: [LEAD, SILENT_PULSE]}
        trace = SearchTrace(
            columns={ChannelName.PULSE1: (tuple(columns[ChannelName.PULSE1]),) * (2 * FRAMES)},
            decoded={ChannelName.PULSE1: (LEAD,) * FRAMES + (FILLER,) * FRAMES},
        )

        assert judged(referee.judge(truth, trace, converted(_held(CHORD)))).score == 0.0

    def test_a_sound_written_as_no_frames_is_left_unjudged(self, referee: SearchReferee) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert referee.judge(truth, _trace({}, {}), converted(_held(CHORD))) is None


class TestFormable:
    PULSE_NOTE: Final[Note] = Note(GeneratorClassName.PULSE_GENERATOR, 64)
    BASS_NOTE: Final[Note] = Note(GeneratorClassName.TRIANGLE_GENERATOR, 48)

    def test_a_channel_s_silence_lets_the_others_form_the_notes(self) -> None:
        options: Dict[ChannelName, FrozenSet[Optional[Note]]] = {
            ChannelName.PULSE1: frozenset({self.PULSE_NOTE}),
            ChannelName.TRIANGLE: frozenset({self.BASS_NOTE, None}),
        }

        assert formable(frozenset({self.PULSE_NOTE}), options)

    def test_a_channel_that_must_sound_adds_a_note_no_choice_removes(self) -> None:
        options: Dict[ChannelName, FrozenSet[Optional[Note]]] = {
            ChannelName.PULSE1: frozenset({self.PULSE_NOTE}),
            ChannelName.TRIANGLE: frozenset({self.BASS_NOTE}),
        }

        assert not formable(frozenset({self.PULSE_NOTE}), options)
