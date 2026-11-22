from dataclasses import dataclass
from typing import Dict, Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.frames import Frame
from sampletones_tools.calibration.referee.notes import NoteReader
from sampletones_tools.calibration.referee.protocol import SCORE_READING, Judgment
from sampletones_tools.calibration.referee.transcription import (
    DUTY,
    MISPLACED,
    MISSED,
    MODE,
    NOTE,
    PERIOD,
    SPURIOUS,
    VOLUME,
    FieldComparison,
    FramePair,
    Misplacements,
    TranscriptionReferee,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .truths import converted, judged, scaled_conversion, written_truth

FRAMES: Final[int] = 4
TOLERANCE: Final[int] = 1
MISPLACED_WEIGHT: Final[float] = 0.75
UNIT_SCALE: Final[float] = 1.0
HALVING_SCALE: Final[float] = 2.0
QUARTER_DUTY: Final[int] = 1
HALF_DUTY: Final[int] = 2
THREE_QUARTERS_DUTY: Final[int] = 3

LEAD_FRAME: Final[PulseInstruction] = PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=HALF_DUTY)
HARMONY_FRAME: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=8, duty_cycle=QUARTER_DUTY)
REST_FRAME: Final[PulseInstruction] = PulseInstruction(on=False, pitch=69, volume=0, duty_cycle=HALF_DUTY)
BASS_FRAME: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=45)
BASS_ON_A_PULSE_FRAME: Final[PulseInstruction] = PulseInstruction(on=True, pitch=33, volume=15, duty_cycle=HALF_DUTY)
SILENT_TRIANGLE_FRAME: Final[TriangleInstruction] = TriangleInstruction(on=False, pitch=45)
HISS_FRAME: Final[NoiseInstruction] = NoiseInstruction(on=True, period=6, volume=10, short=False)

LEAD: Final[List[InstructionUnion]] = [LEAD_FRAME] * FRAMES
HARMONY: Final[List[InstructionUnion]] = [HARMONY_FRAME] * FRAMES
BASS: Final[List[InstructionUnion]] = [BASS_FRAME] * FRAMES
HISS: Final[List[InstructionUnion]] = [HISS_FRAME] * FRAMES
SILENT_PULSE: Final[List[InstructionUnion]] = [REST_FRAME] * FRAMES
SILENT_TRIANGLE: Final[List[InstructionUnion]] = [SILENT_TRIANGLE_FRAME] * FRAMES
BASS_ON_A_PULSE: Final[List[InstructionUnion]] = [BASS_ON_A_PULSE_FRAME] * FRAMES
WRONG_BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=47)] * FRAMES
MELODY_ON_THE_TRIANGLE: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=69 + 12)] * FRAMES


@pytest.fixture(name="referee")
def referee_fixture() -> TranscriptionReferee:
    return TranscriptionReferee(volume_tolerance=TOLERANCE, misplaced_weight=MISPLACED_WEIGHT)


@pytest.fixture(name="comparison")
def comparison_fixture() -> FieldComparison:
    return FieldComparison(volume_tolerance=TOLERANCE, scale=UNIT_SCALE)


@pytest.fixture(name="reader", scope="module")
def reader_fixture() -> NoteReader:
    return NoteReader(Config())


def _judged(referee: TranscriptionReferee, truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(referee.judge(truth, reconstruction))


def _pulse(volume: int, duty_cycle: int, pitch: int) -> List[InstructionUnion]:
    return [PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)] * FRAMES


def _pair(reader: NoteReader, channel: ChannelName, written: Frame, played: Frame) -> FramePair:
    return FramePair(
        written=written,
        played=played,
        written_note=reader.note(channel, written),
        played_note=reader.note(channel, played),
    )


class TestFieldComparison(BaseTestSuite):
    """Each field a channel takes agrees or not, the duty by its timbre and the volume within the tolerance."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        written: InstructionUnion
        played: InstructionUnion
        expected: Dict[str, bool]

    test_cases = (
        TestCase(
            label="pulse_played_as_written",
            written=LEAD_FRAME,
            played=LEAD_FRAME,
            expected={NOTE: True, DUTY: True, VOLUME: True},
        ),
        TestCase(
            label="a_quarter_duty_sounding_three_quarters",
            written=LEAD_FRAME.model_copy(update={"duty_cycle": THREE_QUARTERS_DUTY}),
            played=LEAD_FRAME.model_copy(update={"duty_cycle": QUARTER_DUTY}),
            expected={NOTE: True, DUTY: True, VOLUME: True},
        ),
        TestCase(
            label="a_half_duty_against_a_quarter",
            written=LEAD_FRAME,
            played=LEAD_FRAME.model_copy(update={"duty_cycle": QUARTER_DUTY}),
            expected={NOTE: True, DUTY: False, VOLUME: True},
        ),
        TestCase(
            label="a_volume_at_the_tolerance",
            written=LEAD_FRAME,
            played=LEAD_FRAME.model_copy(update={"volume": LEAD_FRAME.volume + TOLERANCE}),
            expected={NOTE: True, DUTY: True, VOLUME: True},
        ),
        TestCase(
            label="a_volume_past_the_tolerance",
            written=LEAD_FRAME,
            played=LEAD_FRAME.model_copy(update={"volume": LEAD_FRAME.volume - TOLERANCE - 1}),
            expected={NOTE: True, DUTY: True, VOLUME: False},
        ),
        TestCase(
            label="a_triangle_on_another_note",
            written=BASS_FRAME,
            played=BASS_FRAME.model_copy(update={"pitch": BASS_FRAME.pitch + 1}),
            expected={NOTE: False},
        ),
        TestCase(
            label="a_noise_on_another_period_and_mode",
            written=HISS_FRAME,
            played=HISS_FRAME.model_copy(update={"period": HISS_FRAME.period + 1, "short": True}),
            expected={PERIOD: False, MODE: False, VOLUME: True},
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_each_field_the_channel_takes_is_held_against_the_written_one(
        self, comparison: FieldComparison, test_case: TestCase
    ) -> None:
        assert comparison.agreements(test_case.written, test_case.played) == test_case.expected

    def test_a_played_volume_is_read_at_the_working_level_scale(self) -> None:
        halving = FieldComparison(volume_tolerance=TOLERANCE, scale=HALVING_SCALE)
        half = LEAD_FRAME.model_copy(update={"volume": LEAD_FRAME.volume // 2})
        below_half = LEAD_FRAME.model_copy(update={"volume": LEAD_FRAME.volume // 2 - 1})

        assert halving.agreements(LEAD_FRAME, half)[VOLUME]
        assert not halving.agreements(LEAD_FRAME, below_half)[VOLUME]

    def test_frames_of_different_channels_are_refused(self, comparison: FieldComparison) -> None:
        with pytest.raises(TypeError):
            comparison.agreements(LEAD_FRAME, BASS_FRAME)

    def test_disagreements_count_each_field_and_one_for_a_frame_sounding_on_one_side(
        self, comparison: FieldComparison
    ) -> None:
        moved = LEAD_FRAME.model_copy(update={"pitch": LEAD_FRAME.pitch + 1, "duty_cycle": QUARTER_DUTY})

        assert comparison.disagreements(LEAD_FRAME, moved) == 2
        assert comparison.disagreements(LEAD_FRAME, REST_FRAME) == 1
        assert comparison.disagreements(None, LEAD_FRAME) == 1
        assert comparison.disagreements(REST_FRAME, None) == 0


class TestMisplacements:
    """A written note one channel leaves off pairs with a note at its pitch another channel kind adds."""

    def test_a_bass_on_a_pulse_pairs_the_triangle_leaving_it_with_the_pulse_playing_it(
        self, reader: NoteReader
    ) -> None:
        pairs = [
            _pair(reader, ChannelName.PULSE2, REST_FRAME, BASS_ON_A_PULSE_FRAME),
            _pair(reader, ChannelName.TRIANGLE, BASS_FRAME, SILENT_TRIANGLE_FRAME),
        ]

        misplacements = Misplacements.of(pairs)

        assert (misplacements.missing, misplacements.added) == ({1}, {0})
        assert misplacements.passes_through(0) and misplacements.passes_through(1)

    def test_a_note_moved_within_one_channel_kind_is_not_misplaced(self, reader: NoteReader) -> None:
        pairs = [
            _pair(reader, ChannelName.PULSE1, LEAD_FRAME, REST_FRAME),
            _pair(reader, ChannelName.PULSE2, REST_FRAME, LEAD_FRAME),
        ]

        assert Misplacements.of(pairs) == Misplacements(missing=set(), added=set())

    def test_one_added_note_answers_one_missing_note(self, reader: NoteReader) -> None:
        pairs = [
            _pair(reader, ChannelName.TRIANGLE, BASS_FRAME, SILENT_TRIANGLE_FRAME),
            _pair(reader, ChannelName.TRIANGLE, BASS_FRAME, SILENT_TRIANGLE_FRAME),
            _pair(reader, ChannelName.PULSE2, REST_FRAME, BASS_ON_A_PULSE_FRAME),
        ]

        assert Misplacements.of(pairs) == Misplacements(missing={0}, added={2})

    def test_a_frame_played_as_written_holds_no_misplacement(self, reader: NoteReader) -> None:
        pairs = [_pair(reader, ChannelName.TRIANGLE, BASS_FRAME, BASS_FRAME)]

        assert not Misplacements.of(pairs).passes_through(0)


class TestTranscriptionReferee:
    def test_a_conversion_playing_the_frames_as_written_scores_zero(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS, ChannelName.NOISE: HISS}

        assert _judged(referee, written_truth(written), converted(written)).score == 0.0

    def test_the_pulses_count_as_written_whichever_carries_which_line(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}
        swapped = {ChannelName.PULSE1: HARMONY, ChannelName.PULSE2: LEAD}

        assert _judged(referee, written_truth(written), converted(swapped)).score == 0.0

    def test_swapped_pulses_pair_by_the_fields_they_agree_on_where_every_frame_misses(
        self,
        referee: TranscriptionReferee,
    ) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}
        quieter = {ChannelName.PULSE1: _pulse(4, 1, 64), ChannelName.PULSE2: _pulse(4, 2, 69)}

        judgment = _judged(referee, written_truth(written), converted(quieter))

        assert judgment.score == 1.0
        assert (judgment.components[NOTE], judgment.components[DUTY], judgment.components[VOLUME]) == (0.0, 0.0, 1.0)

    def test_pulses_disagreeing_as_much_either_way_are_read_straight(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}
        played = {ChannelName.PULSE1: _pulse(4, QUARTER_DUTY, 69), ChannelName.PULSE2: _pulse(4, HALF_DUTY, 64)}

        judgment = _judged(referee, written_truth(written), converted(played))

        assert (judgment.components[NOTE], judgment.components[DUTY]) == (0.0, 1.0)

    def test_a_quarter_duty_plays_as_written_where_three_quarters_is_written(
        self, referee: TranscriptionReferee
    ) -> None:
        written = {ChannelName.PULSE1: _pulse(12, THREE_QUARTERS_DUTY, 69)}

        judgment = _judged(referee, written_truth(written), converted({ChannelName.PULSE1: _pulse(12, 1, 69)}))

        assert (judgment.score, judgment.components[DUTY]) == (0.0, 0.0)

    def test_a_silent_conversion_misses_every_written_frame(self, referee: TranscriptionReferee) -> None:
        judgment = _judged(
            referee, written_truth({ChannelName.PULSE1: LEAD}), converted({ChannelName.PULSE1: SILENT_PULSE})
        )

        assert judgment.score == 1.0
        assert judgment.components[MISSED] == 1.0

    def test_a_channel_sounding_where_the_writing_is_silent_counts_as_spurious(
        self,
        referee: TranscriptionReferee,
    ) -> None:
        judgment = _judged(
            referee,
            written_truth({ChannelName.PULSE1: LEAD}),
            converted({ChannelName.PULSE1: LEAD, ChannelName.NOISE: HISS}),
        )

        assert judgment.score == pytest.approx(0.5)
        assert judgment.components[SPURIOUS] == pytest.approx(0.5)
        assert judgment.components[MISSED] == 0.0

    def test_frames_neither_side_sounds_go_uncounted(self, referee: TranscriptionReferee) -> None:
        half = FRAMES // 2
        written = {ChannelName.PULSE1: LEAD[:half] + SILENT_PULSE[half:]}
        played = {ChannelName.PULSE1: [LEAD_FRAME, LEAD_FRAME.model_copy(update={"pitch": 70})] + SILENT_PULSE[half:]}

        assert _judged(referee, written_truth(written), converted(played)).score == pytest.approx(0.5)

    def test_a_conversion_shorter_than_its_writing_is_read_over_the_frames_both_describe(
        self, referee: TranscriptionReferee
    ) -> None:
        judgment = _judged(
            referee, written_truth({ChannelName.PULSE1: LEAD}), converted({ChannelName.PULSE1: LEAD[: FRAMES // 2]})
        )

        assert (judgment.score, judgment.components[MISSED]) == (0.0, 0.0)

    def test_a_volume_within_the_tolerance_plays_as_written(self, referee: TranscriptionReferee) -> None:
        judgment = _judged(
            referee,
            written_truth({ChannelName.PULSE1: LEAD}),
            converted({ChannelName.PULSE1: _pulse(12 - TOLERANCE, 2, 69)}),
        )

        assert judgment.readings()[SCORE_READING] == 0.0

    def test_a_volume_past_the_tolerance_counts_against_the_volume(self, referee: TranscriptionReferee) -> None:
        judgment = _judged(
            referee,
            written_truth({ChannelName.PULSE1: LEAD}),
            converted({ChannelName.PULSE1: _pulse(12 - TOLERANCE - 1, 2, 69)}),
        )

        assert judgment.score == 1.0
        assert (judgment.components[VOLUME], judgment.components[NOTE], judgment.components[DUTY]) == (1.0, 0.0, 0.0)

    def test_a_volume_is_read_at_the_level_the_conversion_scaled_the_sound_to(
        self,
        referee: TranscriptionReferee,
    ) -> None:
        written = {ChannelName.PULSE1: _pulse(12, 2, 69)}
        played = {ChannelName.PULSE1: _pulse(6, 2, 69)}

        judgment = _judged(referee, written_truth(written), scaled_conversion(played, HALVING_SCALE))

        assert (judgment.score, judgment.components[VOLUME]) == (0.0, 0.0)

    def test_a_bass_on_a_pulse_counts_once_at_the_weight_of_a_misplaced_note(
        self,
        referee: TranscriptionReferee,
    ) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}
        played = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: BASS_ON_A_PULSE, ChannelName.TRIANGLE: SILENT_TRIANGLE}

        judgment = _judged(referee, written_truth(written), converted(played))

        assert judgment.score == pytest.approx(MISPLACED_WEIGHT / 2)
        assert judgment.components[MISPLACED] == pytest.approx(0.5)
        assert (judgment.components[MISSED], judgment.components[SPURIOUS]) == (0.0, 0.0)

    def test_a_melody_on_the_triangle_is_misplaced_as_a_bass_on_a_pulse_is(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD}
        played = {ChannelName.PULSE1: SILENT_PULSE, ChannelName.TRIANGLE: MELODY_ON_THE_TRIANGLE}

        judgment = _judged(referee, written_truth(written), converted(played))

        assert judgment.score == pytest.approx(MISPLACED_WEIGHT)
        assert judgment.components[MISPLACED] == 1.0

    def test_a_misplaced_bass_weighs_less_than_a_wrong_one(self, referee: TranscriptionReferee) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}
        misplaced = {
            ChannelName.PULSE1: LEAD,
            ChannelName.PULSE2: BASS_ON_A_PULSE,
            ChannelName.TRIANGLE: SILENT_TRIANGLE,
        }
        wrong = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: WRONG_BASS}

        on_a_pulse = _judged(referee, written_truth(written), converted(misplaced)).score
        off_key = _judged(referee, written_truth(written), converted(wrong)).score

        assert on_a_pulse == pytest.approx(MISPLACED_WEIGHT * off_key)

    def test_a_misplaced_bass_beside_a_note_its_channel_adds_counts_the_added_note_too(
        self,
        referee: TranscriptionReferee,
    ) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}
        played = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: BASS_ON_A_PULSE, ChannelName.TRIANGLE: WRONG_BASS}

        judgment = _judged(referee, written_truth(written), converted(played))

        assert judgment.score == pytest.approx((MISPLACED_WEIGHT + 1) / 2)

    def test_a_misplaced_bass_over_a_written_note_of_the_pulse_counts_that_note_wrong(
        self, referee: TranscriptionReferee
    ) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY, ChannelName.TRIANGLE: BASS}
        played = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: BASS_ON_A_PULSE, ChannelName.TRIANGLE: SILENT_TRIANGLE}

        judgment = _judged(referee, written_truth(written), converted(played))

        assert judgment.score == pytest.approx((MISPLACED_WEIGHT + 1) / 3)

    @pytest.mark.xfail(
        strict=True,
        reason="suspected bug: the channel leaving a misplaced note off charges its own wrong note on the same frame",
    )
    def test_the_score_stays_a_share_where_a_misplaced_note_meets_a_wrong_one(
        self, referee: TranscriptionReferee
    ) -> None:
        played = {ChannelName.TRIANGLE: WRONG_BASS, ChannelName.PULSE2: BASS_ON_A_PULSE}

        judgment = _judged(referee, written_truth({ChannelName.TRIANGLE: BASS}), converted(played))

        assert judgment.score <= 1.0

    def test_every_field_the_noise_takes_is_read(self, referee: TranscriptionReferee) -> None:
        played = [NoiseInstruction(on=True, period=7, volume=10, short=True)] * FRAMES

        judgment = _judged(referee, written_truth({ChannelName.NOISE: HISS}), converted({ChannelName.NOISE: played}))

        assert (judgment.components[PERIOD], judgment.components[MODE], judgment.components[VOLUME]) == (1.0, 1.0, 0.0)

    def test_a_sound_and_a_conversion_both_silent_are_left_unjudged(self, referee: TranscriptionReferee) -> None:
        silent = {ChannelName.PULSE1: SILENT_PULSE}

        assert referee.judge(written_truth(silent), converted(silent)) is None

    def test_a_synthesized_sound_written_as_no_frames_is_left_unjudged(self, referee: TranscriptionReferee) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert referee.judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
