from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import PitchLine, Truth
from sampletones_tools.calibration.referee.balance import (
    BASS_ON_A_PULSE,
    NOISE,
    PULSES,
    SCALE,
    TRIANGLE,
    BalanceReferee,
    bass_on_pulse,
    part_shares,
)
from sampletones_tools.calibration.referee.protocol import Judgment

from .truths import converted, judged, scaled_conversion, written_truth

FRAMES: Final[int] = 4
BASS: Final[List[InstructionUnion]] = [TriangleInstruction(on=True, pitch=57)] * FRAMES
LEAD: Final[List[InstructionUnion]] = [PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=2)] * FRAMES
HARMONY: Final[List[InstructionUnion]] = [PulseInstruction(on=True, pitch=64, volume=8, duty_cycle=1)] * FRAMES
HALVING_SCALE: Final[float] = 2.0
BASS_FREQUENCY: Final[float] = 110.0
OTHER_FREQUENCY: Final[float] = 130.8
WRITTEN_BASS: Final[Dict[ChannelName, PitchLine]] = {ChannelName.TRIANGLE: (BASS_FREQUENCY, None, BASS_FREQUENCY)}


def _judged(truth: Truth, reconstruction: Reconstruction) -> Judgment:
    return judged(BalanceReferee().judge(truth, reconstruction))


class TestPartShares:
    def test_the_pulses_share_as_one_part(self) -> None:
        audio = {channel: np.ones(4) for channel in (ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE)}

        assert part_shares(audio) == pytest.approx({PULSES: 2 / 3, TRIANGLE: 1 / 3, NOISE: 0.0})

    def test_a_silent_render_holds_no_share(self) -> None:
        assert part_shares({ChannelName.PULSE1: np.zeros(4)}) == {PULSES: 0.0, TRIANGLE: 0.0, NOISE: 0.0}


class TestBassOnPulse:
    def test_a_pulse_sounding_the_bass_in_another_octave_takes_it(self) -> None:
        played = {ChannelName.PULSE1: (2 * BASS_FREQUENCY,) * 3}

        assert bass_on_pulse(WRITTEN_BASS, played) == 1.0

    def test_a_triangle_sounding_the_bass_in_any_octave_keeps_it(self) -> None:
        played = {ChannelName.TRIANGLE: (2 * BASS_FREQUENCY,) * 3, ChannelName.PULSE1: (BASS_FREQUENCY,) * 3}

        assert bass_on_pulse(WRITTEN_BASS, played) == 0.0

    def test_a_pulse_on_another_note_takes_nothing(self) -> None:
        played = {ChannelName.PULSE1: (OTHER_FREQUENCY,) * 3}

        assert bass_on_pulse(WRITTEN_BASS, played) == 0.0

    def test_only_the_bass_s_sounding_frames_count(self) -> None:
        played = {ChannelName.TRIANGLE: (None, None, BASS_FREQUENCY), ChannelName.PULSE2: (BASS_FREQUENCY, None, None)}

        assert bass_on_pulse(WRITTEN_BASS, played) == pytest.approx(0.5)

    def test_a_writing_with_no_triangle_holds_no_bass_to_take(self) -> None:
        assert bass_on_pulse({}, {ChannelName.PULSE1: (BASS_FREQUENCY,)}) == 0.0
        assert bass_on_pulse({ChannelName.TRIANGLE: (None, None)}, {ChannelName.PULSE1: (BASS_FREQUENCY,) * 2}) == 0.0


class TestBalanceReferee:
    def test_a_conversion_playing_the_sound_as_written_scores_zero_at_unit_scale(self) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: BASS}

        judgment = _judged(written_truth(written), converted(written))

        assert judgment.score == pytest.approx(0.0)
        assert judgment.components[SCALE] == pytest.approx(1.0)
        assert judgment.components[BASS_ON_A_PULSE] == 0.0

    def test_a_bass_line_moved_to_a_pulse_starves_the_triangle(self) -> None:
        moved = [PulseInstruction(on=True, pitch=45, volume=10, duty_cycle=2)] * FRAMES

        judgment = _judged(written_truth({ChannelName.TRIANGLE: BASS}), converted({ChannelName.PULSE1: moved}))

        assert judgment.score == pytest.approx(1.0)
        assert judgment.components[TRIANGLE] == pytest.approx(-1.0)
        assert judgment.components[PULSES] == pytest.approx(1.0)
        assert judgment.components[BASS_ON_A_PULSE] == 1.0

    def test_the_pulses_share_as_one_part_whichever_carries_which_line(self) -> None:
        written = {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY}
        swapped = {ChannelName.PULSE1: HARMONY, ChannelName.PULSE2: LEAD}

        assert _judged(written_truth(written), converted(swapped)).score == pytest.approx(0.0)

    def test_the_scale_reading_is_the_working_level_the_conversion_matched_at(self) -> None:
        written = {ChannelName.PULSE1: LEAD}

        judgment = _judged(written_truth(written), scaled_conversion(written, HALVING_SCALE))

        assert judgment.components[SCALE] == pytest.approx(HALVING_SCALE)
        assert judgment.score == pytest.approx(0.0)

    def test_a_synthesized_sound_written_as_no_frames_is_left_unjudged(self) -> None:
        truth = Truth(instructions={}, pitches={"bass": (110.0,) * FRAMES})

        assert BalanceReferee().judge(truth, converted({ChannelName.TRIANGLE: BASS})) is None
