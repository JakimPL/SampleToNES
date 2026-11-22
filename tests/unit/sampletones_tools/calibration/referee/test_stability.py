from typing import Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.referee.protocol import Judgment
from sampletones_tools.calibration.referee.stability import (
    DECIBELS_PER_AMPLITUDE_DECADE,
    DUTY_SWITCHES,
    LEVEL_MOTION,
    MOVES,
    PITCH_MOTION,
    TOGGLES,
    Changes,
    StabilityReferee,
    duty_switches,
    level_motion,
    line_changes,
    pitch_motion,
    stream_changes,
)

from .truths import converted, judged, written_truth

FRAMES: Final[int] = 60
ON: Final[InstructionUnion] = TriangleInstruction(on=True, pitch=45)
OFF: Final[InstructionUnion] = TriangleInstruction(on=False, pitch=45)
UP: Final[InstructionUnion] = TriangleInstruction(on=True, pitch=47)
SECONDS: Final[float] = FRAMES / Config().library.nes_frequency
SEMITONE_RATIO: Final[float] = 2.0 ** (1.0 / 12.0)
QUARTER_DUTY: Final[int] = 1
HALF_DUTY: Final[int] = 2
THREE_QUARTERS_DUTY: Final[int] = 3


def _flickering(times: int) -> List[InstructionUnion]:
    stream = [ON] * FRAMES
    for frame in range(times):
        stream[2 * frame + 1] = OFF

    return stream


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(StabilityReferee().judge(truth, reconstruction))


def _pulse(volume: int, duty_cycle: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=69, volume=volume, duty_cycle=duty_cycle)


class TestChangeCounts:
    def test_a_channel_turning_off_and_on_toggles_twice_and_a_new_note_moves_once(self) -> None:
        changes = stream_changes({ChannelName.TRIANGLE: [ON, OFF, ON, UP, UP]}, 5)

        assert changes == Changes(toggles=2, moves=1)

    def test_a_noise_moves_where_its_period_changes(self) -> None:
        hiss = NoiseInstruction(on=True, period=6, volume=10, short=False)

        changes = stream_changes({ChannelName.NOISE: [hiss, hiss.model_copy(update={"period": 7})]}, 2)

        assert changes == Changes(toggles=0, moves=1)

    def test_changes_past_the_length_go_uncounted(self) -> None:
        assert stream_changes({ChannelName.TRIANGLE: [ON, ON, OFF]}, 2) == Changes(toggles=0, moves=0)

    def test_a_line_toggles_where_it_starts_or_stops_and_moves_to_another_note(self) -> None:
        line = (None, 110.0, 110.0 * SEMITONE_RATIO, None)

        assert line_changes({"bass": line}, len(line)) == Changes(toggles=2, moves=1)

    def test_a_line_wavering_within_its_semitone_holds_its_note(self) -> None:
        line = (110.0, 110.0 * 2.0 ** (0.3 / 12.0), 110.0)

        assert line_changes({"bass": line}, len(line)) == Changes(toggles=0, moves=0)


class TestMotion:
    def test_pitch_motion_sums_the_semitones_between_sounding_frames(self) -> None:
        line = (110.0, 110.0 * SEMITONE_RATIO, None, 110.0)

        assert pitch_motion([line], len(line)) == pytest.approx(1.0)

    def test_level_motion_reads_a_doubled_volume_as_its_decibels(self) -> None:
        stream: List[InstructionUnion] = [_pulse(4, HALF_DUTY), _pulse(8, HALF_DUTY)]

        assert level_motion({ChannelName.PULSE1: stream}, 2) == pytest.approx(DECIBELS_PER_AMPLITUDE_DECADE * 0.30103)

    def test_a_step_to_or_from_volume_zero_moves_no_level(self) -> None:
        stream: List[InstructionUnion] = [_pulse(8, HALF_DUTY), _pulse(0, HALF_DUTY), _pulse(4, HALF_DUTY)]

        assert level_motion({ChannelName.PULSE1: stream}, 3) == 0.0

    def test_the_triangle_holds_no_level(self) -> None:
        assert level_motion({ChannelName.TRIANGLE: [ON, UP]}, 2) == 0.0

    def test_a_duty_switch_counts_where_the_timbre_changes(self) -> None:
        stream: List[InstructionUnion] = [
            _pulse(8, QUARTER_DUTY),
            _pulse(8, THREE_QUARTERS_DUTY),
            _pulse(8, HALF_DUTY),
            PulseInstruction(on=False, pitch=69, volume=8, duty_cycle=QUARTER_DUTY),
            _pulse(8, QUARTER_DUTY),
        ]

        assert duty_switches({ChannelName.PULSE1: stream}, len(stream)) == 1


class TestStabilityReferee:
    def test_a_conversion_changing_where_its_sound_does_scores_zero(self) -> None:
        stream = [ON] * (FRAMES // 2) + [UP] * (FRAMES // 2)

        judgment = _judged(written_truth({ChannelName.TRIANGLE: stream}), converted({ChannelName.TRIANGLE: stream}))

        assert judgment.score == 0.0

    def test_every_turn_off_and_back_on_beyond_the_sound_s_own_counts_twice(self) -> None:
        judgment = _judged(
            written_truth({ChannelName.TRIANGLE: [ON] * FRAMES}), converted({ChannelName.TRIANGLE: _flickering(3)})
        )

        assert judgment.components[TOGGLES] == pytest.approx(6 / SECONDS)
        assert judgment.components[MOVES] == 0.0

    def test_a_conversion_changing_less_than_its_sound_reads_zero(self) -> None:
        judgment = _judged(
            written_truth({ChannelName.TRIANGLE: _flickering(3)}), converted({ChannelName.TRIANGLE: [ON] * FRAMES})
        )

        assert judgment.score == 0.0

    def test_a_synthesized_sound_changes_where_its_lines_move_to_another_note(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * (FRAMES // 2) + (123.5,) * (FRAMES // 2)})
        stream = [TriangleInstruction(on=True, pitch=57)] * (FRAMES // 2) + [TriangleInstruction(on=True, pitch=59)] * (
            FRAMES // 2
        )

        judgment = _judged(truth, converted({ChannelName.TRIANGLE: stream}))

        assert judgment.score == 0.0
        assert LEVEL_MOTION not in judgment.components
        assert DUTY_SWITCHES not in judgment.components

    def test_a_sound_and_a_conversion_sharing_no_frame_are_left_unjudged(self) -> None:
        assert StabilityReferee().judge(Truth(instructions={}, pitches={}), converted({})) is None


class TestMotionReadings:
    def test_a_bend_the_sound_itself_makes_counts_as_the_sound_s_own(self) -> None:
        wobbling = [TriangleInstruction(on=True, pitch=45, detune=offset) for offset in (0, 1, 0, -1) * (FRAMES // 4)]

        judgment = _judged(written_truth({ChannelName.TRIANGLE: wobbling}), converted({ChannelName.TRIANGLE: wobbling}))

        assert judgment.components[PITCH_MOTION] == 0.0

    def test_a_bend_the_sound_lacks_reads_as_pitch_motion(self) -> None:
        wobbling = [TriangleInstruction(on=True, pitch=45, detune=offset) for offset in (0, 1, 0, -1) * (FRAMES // 4)]

        judgment = _judged(
            written_truth({ChannelName.TRIANGLE: [ON] * FRAMES}), converted({ChannelName.TRIANGLE: wobbling})
        )

        assert judgment.components[PITCH_MOTION] > 0.0

    def test_a_volume_that_flutters_where_the_sound_holds_reads_as_level_motion(self) -> None:
        held = [_pulse(8, HALF_DUTY)] * FRAMES
        fluttering = [_pulse(8 + frame % 2, HALF_DUTY) for frame in range(FRAMES)]

        judgment = _judged(written_truth({ChannelName.PULSE1: held}), converted({ChannelName.PULSE1: fluttering}))

        assert judgment.components[LEVEL_MOTION] > 0.0

    def test_a_pulse_switching_between_a_quarter_and_three_quarters_keeps_its_timbre(self) -> None:
        held = [_pulse(8, QUARTER_DUTY)] * FRAMES
        switching = [_pulse(8, QUARTER_DUTY + 2 * (frame % 2)) for frame in range(FRAMES)]

        judgment = _judged(written_truth({ChannelName.PULSE1: held}), converted({ChannelName.PULSE1: switching}))

        assert judgment.components[DUTY_SWITCHES] == 0.0
