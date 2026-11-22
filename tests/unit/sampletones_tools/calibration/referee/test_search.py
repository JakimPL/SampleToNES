from dataclasses import dataclass, replace
from typing import Dict, Final, FrozenSet, List, Mapping, Optional, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.notes import Note
from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.referee.search import (
    ASSIGNMENT,
    AT_CHANGE,
    AWAY_FROM_CHANGE,
    COLUMNS,
    DECODER,
    GAINS,
    MISPLACED,
    NEXT_TO_CHANGE,
    POOLED,
    UNREACHED,
    SearchFrame,
    SearchReferee,
    change_distances,
    formable,
    poolable,
)
from sampletones_tools.calibration.trace import InstructionColumn, PoolTrace, SearchTrace
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

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
LEAD_NOTE: Final[Note] = Note(kind=GeneratorClassName.PULSE_GENERATOR, semitone=64)
HARMONY_NOTE: Final[Note] = Note(kind=GeneratorClassName.PULSE_GENERATOR, semitone=67)
BASS_NOTE: Final[Note] = Note(kind=GeneratorClassName.TRIANGLE_GENERATOR, semitone=48)
BASS_ON_A_PULSE_NOTE: Final[Note] = Note(kind=GeneratorClassName.PULSE_GENERATOR, semitone=48)
AWAY_FROM_ANY_CHANGE: Final[int] = 5
SILENCES: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: SILENT_PULSE,
    ChannelName.PULSE2: SILENT_PULSE,
    ChannelName.TRIANGLE: SILENT_TRIANGLE,
}


@pytest.fixture(name="referee")
def referee_fixture() -> SearchReferee:
    return SearchReferee()


@pytest.fixture(name="right_frame")
def right_frame_fixture() -> SearchFrame:
    """A frame of a lead over a bass the columns offer, the picks hold and the decoder keeps."""
    written = frozenset({LEAD_NOTE, BASS_NOTE})
    return SearchFrame(
        target=written,
        options={
            ChannelName.PULSE1: frozenset({LEAD_NOTE, None}),
            ChannelName.PULSE2: frozenset({None}),
            ChannelName.TRIANGLE: frozenset({BASS_NOTE, None}),
        },
        heads=written,
        decoded=written,
        pools=None,
        change_distance=AWAY_FROM_ANY_CHANGE,
    )


def _held(frames: Mapping[ChannelName, InstructionUnion]) -> Dict[ChannelName, List[InstructionUnion]]:
    return {channel: [instruction] * FRAMES for channel, instruction in frames.items()}


def _trace(
    columns: Mapping[ChannelName, Sequence[InstructionUnion]],
    decoded: Mapping[ChannelName, InstructionUnion],
) -> SearchTrace:
    """A search offering the same column and decoding the same frame on every frame of each channel."""
    return _pooled_trace(columns, decoded, {})


def _pooled_trace(
    columns: Mapping[ChannelName, Sequence[InstructionUnion]],
    decoded: Mapping[ChannelName, InstructionUnion],
    pools: Mapping[Tuple[ChannelName, ...], Sequence[Tuple[InstructionUnion, ...]]],
) -> SearchTrace:
    """A search as ``_trace`` reads it that also pools the same combinations on every frame, one stem per entry."""
    held: Dict[ChannelName, Tuple[InstructionColumn, ...]] = {
        channel: (tuple(column),) * FRAMES for channel, column in columns.items()
    }
    return SearchTrace(
        columns=held,
        pools={
            stem_id: PoolTrace(channel_names=channel_names, frames=(tuple(combinations),) * FRAMES)
            for stem_id, (channel_names, combinations) in enumerate(pools.items())
        },
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

        assert readings[SCORE_READING] == 0.0
        assert (readings[UNREACHED], readings[GAINS]) == (0.0, 0.0)

    def test_notes_no_column_offers_are_lost_at_the_columns(self, referee: SearchReferee) -> None:
        columns = {
            ChannelName.PULSE1: [LEAD, SILENT_PULSE],
            ChannelName.PULSE2: [FILLER, SILENT_PULSE],
            ChannelName.TRIANGLE: [SILENT_TRIANGLE],
        }
        decoded = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: FILLER, ChannelName.TRIANGLE: SILENT_TRIANGLE}

        readings = _judged(referee, CHORD_TRUTH, _trace(columns, decoded))

        assert (readings[SCORE_READING], readings[COLUMNS]) == (1.0, 1.0)
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

        assert (readings[SCORE_READING], readings[DECODER]) == (1.0, 1.0)

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

        assert (readings[SCORE_READING], readings[GAINS]) == (0.0, 1.0)

    def test_a_bass_decoded_on_a_pulse_is_wrong_and_reads_as_misplaced(self, referee: SearchReferee) -> None:
        columns = {
            ChannelName.PULSE1: [LEAD, SILENT_PULSE],
            ChannelName.PULSE2: [BASS_ON_A_PULSE, HARMONY, SILENT_PULSE],
            ChannelName.TRIANGLE: [SILENT_TRIANGLE],
        }
        decoded = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: BASS_ON_A_PULSE, ChannelName.TRIANGLE: SILENT_TRIANGLE}
        truth = written_truth(_held({ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}))

        readings = _judged(referee, truth, _trace(columns, decoded))

        assert (readings[SCORE_READING], readings[MISPLACED], readings[COLUMNS]) == (1.0, 1.0, 1.0)

    def test_frames_the_writing_leaves_silent_go_uncounted(self, referee: SearchReferee) -> None:
        rest: List[InstructionUnion] = [SILENT_PULSE] * FRAMES
        truth = written_truth({ChannelName.PULSE1: [LEAD] * FRAMES + rest})
        columns = {ChannelName.PULSE1: [LEAD, SILENT_PULSE]}
        trace = SearchTrace(
            columns={ChannelName.PULSE1: (tuple(columns[ChannelName.PULSE1]),) * (2 * FRAMES)},
            pools={},
            decoded={ChannelName.PULSE1: (LEAD,) * FRAMES + (FILLER,) * FRAMES},
        )

        assert judged(referee.judge(truth, trace, converted(_held(CHORD)))).score == 0.0

    def test_a_sound_written_as_no_frames_is_left_unjudged(self, referee: SearchReferee) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert referee.judge(truth, _trace({}, {}), converted(_held(CHORD))) is None


class TestSearchFrame:
    """A frame is right where it decodes the written notes, and lost at the first stage that missed them."""

    LEAD_ALONE: Final[FrozenSet[Note]] = frozenset({LEAD_NOTE})

    def test_a_frame_decoding_the_written_notes_is_right_and_lost_nowhere(self, right_frame: SearchFrame) -> None:
        assert right_frame.right and right_frame.lost_at is None
        assert not (right_frame.gained or right_frame.misplaced)
        assert (right_frame.unreached, right_frame.pooled) == (0, None)

    def test_a_decoder_putting_wrong_picks_right_gains_the_frame(self, right_frame: SearchFrame) -> None:
        assert replace(right_frame, heads=self.LEAD_ALONE).gained

    def test_notes_no_column_offers_are_lost_at_the_columns(self, right_frame: SearchFrame) -> None:
        options = {**right_frame.options, ChannelName.TRIANGLE: frozenset({None})}
        frame = replace(right_frame, options=options, heads=self.LEAD_ALONE, decoded=self.LEAD_ALONE)

        assert (frame.lost_at, frame.unreached) == (COLUMNS, 1)

    def test_picks_missing_notes_the_columns_hold_lose_them_at_the_assignment(self, right_frame: SearchFrame) -> None:
        frame = replace(right_frame, heads=self.LEAD_ALONE, decoded=self.LEAD_ALONE)

        assert frame.lost_at == ASSIGNMENT

    def test_a_decoder_moving_off_picks_that_held_the_notes_loses_them(self, right_frame: SearchFrame) -> None:
        assert replace(right_frame, decoded=self.LEAD_ALONE).lost_at == DECODER

    def test_a_bass_decoded_on_a_pulse_reads_as_misplaced(self, right_frame: SearchFrame) -> None:
        frame = replace(right_frame, decoded=frozenset({LEAD_NOTE, BASS_ON_A_PULSE_NOTE}))

        assert frame.misplaced and not frame.right

    @pytest.mark.xfail(strict=True, reason="suspected bug: a note lost from a unison across kinds reads as misplaced")
    def test_a_note_lost_from_a_unison_across_kinds_is_no_misplacement(self, right_frame: SearchFrame) -> None:
        unison = frozenset({BASS_NOTE, BASS_ON_A_PULSE_NOTE})
        frame = replace(right_frame, target=unison, heads=unison, decoded=frozenset({BASS_ON_A_PULSE_NOTE}))

        assert not frame.misplaced

    def test_a_search_pooling_combinations_reads_whether_its_pools_hold_the_notes(
        self, right_frame: SearchFrame
    ) -> None:
        holding = [frozenset({frozenset({LEAD_NOTE, BASS_NOTE})})]
        missing = [frozenset({frozenset({LEAD_NOTE})})]

        assert replace(right_frame, pools=holding).pooled is True
        assert replace(right_frame, pools=missing).pooled is False


class TestChangeReading(BaseTestSuite):
    """A frame reads at a change, next to one, or away from one by its distance to the nearest change."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        distance: int
        expected: str

    test_cases = (
        TestCase(label="at_a_change", distance=0, expected=AT_CHANGE),
        TestCase(label="one_frame_from_a_change", distance=1, expected=NEXT_TO_CHANGE),
        TestCase(label="two_frames_from_a_change", distance=2, expected=AWAY_FROM_CHANGE),
        TestCase(label="far_from_any_change", distance=AWAY_FROM_ANY_CHANGE, expected=AWAY_FROM_CHANGE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_frame_counts_in_the_reading_its_distance_names(
        self, right_frame: SearchFrame, test_case: TestCase
    ) -> None:
        assert replace(right_frame, change_distance=test_case.distance).change_reading == test_case.expected


class TestThePooledReading:
    """The pooled reading counts frames whose pools can sound the written notes, one combination per stem."""

    MISSED: Final[Dict[ChannelName, InstructionUnion]] = {
        ChannelName.PULSE1: LEAD,
        ChannelName.PULSE2: FILLER,
        ChannelName.TRIANGLE: SILENT_TRIANGLE,
    }
    COLUMNS: Final[Dict[ChannelName, List[InstructionUnion]]] = {
        channel: [frame, SILENCES[channel]] for channel, frame in MISSED.items()
    }
    TONAL: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE)

    def test_a_pool_holding_the_written_notes_reads_as_pooled(self, referee: SearchReferee) -> None:
        pools = {self.TONAL: [(LEAD, FILLER, SILENT_TRIANGLE), (HARMONY, LEAD, BASS)]}

        readings = _judged(referee, CHORD_TRUTH, _pooled_trace(self.COLUMNS, self.MISSED, pools))

        assert (readings[SCORE_READING], readings[POOLED]) == (1.0, 1.0)

    def test_a_pool_missing_the_written_notes_reads_as_unpooled(self, referee: SearchReferee) -> None:
        pools = {self.TONAL: [(LEAD, FILLER, SILENT_TRIANGLE), (LEAD, HARMONY, SILENT_TRIANGLE)]}

        readings = _judged(referee, CHORD_TRUTH, _pooled_trace(self.COLUMNS, self.MISSED, pools))

        assert readings[POOLED] == 0.0

    @pytest.mark.parametrize(
        "bass_pool, pooled",
        [([(BASS,), (SILENT_TRIANGLE,)], 1.0), ([(SILENT_TRIANGLE,)], 0.0)],
        ids=["each stem holds its part", "a stem lacks its part"],
    )
    def test_the_stems_pools_sound_the_written_notes_together(
        self,
        referee: SearchReferee,
        bass_pool: List[Tuple[InstructionUnion, ...]],
        pooled: float,
    ) -> None:
        pools = {
            (ChannelName.PULSE1, ChannelName.PULSE2): [(LEAD, HARMONY), (FILLER, SILENT_PULSE)],
            (ChannelName.TRIANGLE,): bass_pool,
        }

        readings = _judged(referee, CHORD_TRUTH, _pooled_trace(self.COLUMNS, self.MISSED, pools))

        assert readings[POOLED] == pooled

    def test_a_search_pooling_nothing_has_no_pooled_reading(self, referee: SearchReferee) -> None:
        readings = _judged(referee, CHORD_TRUTH, _trace(self.COLUMNS, self.MISSED))

        assert POOLED not in readings


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

    def test_a_channel_offering_silence_alone_forms_no_note(self) -> None:
        options: Dict[ChannelName, FrozenSet[Optional[Note]]] = {ChannelName.TRIANGLE: frozenset({None})}

        assert not formable(frozenset({self.BASS_NOTE}), options)
        assert formable(frozenset(), options)


class TestPoolable:
    PULSE_NOTE: Final[Note] = Note(GeneratorClassName.PULSE_GENERATOR, 64)
    BASS_NOTE: Final[Note] = Note(GeneratorClassName.TRIANGLE_GENERATOR, 48)

    def test_the_stems_combinations_join_into_the_written_notes(self) -> None:
        pools = [frozenset({frozenset({self.PULSE_NOTE})}), frozenset({frozenset({self.BASS_NOTE}), frozenset()})]

        assert poolable(frozenset({self.PULSE_NOTE, self.BASS_NOTE}), pools)

    def test_a_combination_sounding_a_note_beyond_the_written_ones_joins_no_match(self) -> None:
        pools = [frozenset({frozenset({self.PULSE_NOTE, self.BASS_NOTE})})]

        assert not poolable(frozenset({self.PULSE_NOTE}), pools)

    def test_a_stem_whose_pool_is_empty_matches_nothing(self) -> None:
        pools = [frozenset({frozenset({self.PULSE_NOTE})}), frozenset()]

        assert not poolable(frozenset({self.PULSE_NOTE}), pools)

    def test_no_pool_sounds_only_silence(self) -> None:
        assert poolable(frozenset(), [])
        assert not poolable(frozenset({self.PULSE_NOTE}), [])


class TestTheChangeReadings:
    """A frame's analysis window reads its neighbors, so the frames near a written note change are read apart."""

    def test_a_frame_stands_as_far_from_a_change_as_the_nearest_frame_beside_one(self) -> None:
        lead, harmony = (LEAD_NOTE,), (HARMONY_NOTE,)

        distances = change_distances([lead, lead, lead, harmony, harmony, harmony, harmony])

        assert distances == [2, 1, 0, 0, 1, 2, 3]

    def test_a_writing_without_a_change_stands_away_from_one_throughout(self) -> None:
        assert change_distances([(LEAD_NOTE,)] * FRAMES) == [FRAMES] * FRAMES

    def test_a_change_between_the_first_two_frames_stands_both_at_it(self) -> None:
        lead, harmony = (LEAD_NOTE,), (HARMONY_NOTE,)

        assert change_distances([lead, harmony, harmony, harmony]) == [0, 0, 1, 2]

    def test_a_channel_falling_silent_is_a_change(self) -> None:
        assert change_distances([(LEAD_NOTE,), (None,), (None,)]) == [0, 0, 1]

    def test_a_single_frame_or_none_stand_as_far_as_the_writing_is_long(self) -> None:
        assert change_distances([(LEAD_NOTE,)]) == [1]
        assert not change_distances([])

    def test_a_held_line_decoded_through_a_change_is_wrong_on_the_changed_side(self, referee: SearchReferee) -> None:
        truth = written_truth({ChannelName.PULSE1: [LEAD, LEAD, HARMONY, HARMONY]})
        trace = _trace({ChannelName.PULSE1: [LEAD, HARMONY, SILENT_PULSE]}, {ChannelName.PULSE1: LEAD})

        readings = _judged(referee, truth, trace)

        assert (readings[AT_CHANGE], readings[NEXT_TO_CHANGE]) == (0.5, 0.5)
        assert AWAY_FROM_CHANGE not in readings

    def test_a_held_chord_is_read_away_from_any_change(self, referee: SearchReferee) -> None:
        trace = _trace({channel: [frame, SILENCES[channel]] for channel, frame in CHORD.items()}, CHORD)

        readings = _judged(referee, CHORD_TRUTH, trace)

        assert readings[AWAY_FROM_CHANGE] == 0.0
        assert AT_CHANGE not in readings
