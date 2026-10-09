from dataclasses import dataclass
from itertools import product
from typing import Any, Final, Tuple

import pytest

from sampletones_core.constants.general import (
    MAX_PITCH,
    MAX_VOLUME,
    MIN_PITCH,
    MIN_PLAYED_PITCH,
    MIN_VOLUME,
    SILENT_VOLUME,
    VOLUME_RANGE,
)
from sampletones_core.instructions import (
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.performance import apply_modifiers
from sampletones_core.performance.modifiers import triangle_sounds_at
from tests.suite.case import BaseRegularTestCase, BaseTestCase

LEVEL_PAIRS: Final[Tuple[Tuple[int, int], ...]] = tuple(product(VOLUME_RANGE, VOLUME_RANGE))


def _pulse(volume: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=60, volume=volume, duty_cycle=0)


def _noise(volume: int) -> NoiseInstruction:
    return NoiseInstruction(on=True, period=3, volume=volume, short=False)


@dataclass(frozen=True, kw_only=True)
class VolumeScalingCase(BaseRegularTestCase):
    instruction_volume: int
    row_volume: int
    expected: Any


VOLUME_SCALING_CASES = [
    VolumeScalingCase(
        label="max×max",
        instruction_volume=15,
        row_volume=15,
        expected=15,
    ),
    VolumeScalingCase(
        label="half×half",
        instruction_volume=8,
        row_volume=8,
        expected=4,
    ),
    VolumeScalingCase(
        label="zero row",
        instruction_volume=15,
        row_volume=0,
        expected=0,
    ),
    VolumeScalingCase(
        label="zero instruction",
        instruction_volume=0,
        row_volume=15,
        expected=0,
    ),
    VolumeScalingCase(
        label="max×half",
        instruction_volume=15,
        row_volume=7,
        expected=7,
    ),
    VolumeScalingCase(
        label="one×one",
        instruction_volume=1,
        row_volume=1,
        expected=0,
    ),
    VolumeScalingCase(
        label="ten×ten",
        instruction_volume=10,
        row_volume=10,
        expected=7,
    ),
    VolumeScalingCase(
        label="max×mid",
        instruction_volume=15,
        row_volume=8,
        expected=8,
    ),
]


class TestPulseVolumeScaling:
    @pytest.mark.parametrize("case", VOLUME_SCALING_CASES, ids=lambda c: c.label)
    def test_volume_scaled_correctly(
        self,
        case: VolumeScalingCase,
    ) -> None:
        result = apply_modifiers(
            _pulse(case.instruction_volume),
            transpose=0,
            row_volume=case.row_volume,
        )
        assert isinstance(result, PulseInstruction)
        assert result.volume == case.expected

    def test_every_pair_of_levels_rounds_to_the_nearest_step(self) -> None:
        sounded = {
            (volume, row_volume): apply_modifiers(_pulse(volume), transpose=0, row_volume=row_volume).volume
            for volume, row_volume in LEVEL_PAIRS
        }

        assert sounded == {
            (volume, row_volume): round(volume * row_volume / MAX_VOLUME) for volume, row_volume in LEVEL_PAIRS
        }


NOISE_VOLUME_CASES = [
    VolumeScalingCase(label="max×max", instruction_volume=15, row_volume=15, expected=15),
    VolumeScalingCase(label="a fraction rounds down", instruction_volume=13, row_volume=8, expected=6),
    VolumeScalingCase(label="ten×ten rounds down", instruction_volume=10, row_volume=10, expected=6),
    VolumeScalingCase(label="one×one keeps the quietest level", instruction_volume=1, row_volume=1, expected=1),
    VolumeScalingCase(label="a quiet row keeps a loud note audible", instruction_volume=15, row_volume=1, expected=1),
    VolumeScalingCase(label="a quiet note under a loud row", instruction_volume=1, row_volume=14, expected=1),
    VolumeScalingCase(label="the loudest product below one step", instruction_volume=7, row_volume=2, expected=1),
    VolumeScalingCase(label="a silent row silences", instruction_volume=15, row_volume=0, expected=0),
    VolumeScalingCase(label="a silent instruction stays silent", instruction_volume=0, row_volume=15, expected=0),
]


class TestNoiseVolumeScaling:
    """The noise level follows the rule FamiTracker and Bitphase share: the product rounded down, and the
    quietest level wherever that comes out silent while both levels sound."""

    @pytest.mark.parametrize("case", NOISE_VOLUME_CASES, ids=lambda c: c.label)
    def test_volume_scaled_correctly(
        self,
        case: VolumeScalingCase,
    ) -> None:
        result = apply_modifiers(
            _noise(case.instruction_volume),
            transpose=0,
            row_volume=case.row_volume,
        )
        assert isinstance(result, NoiseInstruction)
        assert result.volume == case.expected

    def test_every_pair_of_levels_follows_the_trackers_rule(self) -> None:
        sounded = {
            (volume, row_volume): apply_modifiers(_noise(volume), transpose=0, row_volume=row_volume).volume
            for volume, row_volume in LEVEL_PAIRS
        }

        assert sounded == {
            (volume, row_volume): (
                max(MIN_VOLUME, volume * row_volume // MAX_VOLUME) if volume * row_volume else SILENT_VOLUME
            )
            for volume, row_volume in LEVEL_PAIRS
        }


@dataclass(frozen=True, kw_only=True)
class PulseTransposeCase(BaseTestCase):
    label: str
    pitch: int
    transpose: int
    expected_pitch: int


PULSE_TRANSPOSE_CASES = [
    PulseTransposeCase(
        label="shift +5",
        pitch=60,
        transpose=5,
        expected_pitch=65,
    ),
    PulseTransposeCase(
        label="shift -12",
        pitch=60,
        transpose=-12,
        expected_pitch=48,
    ),
    PulseTransposeCase(
        label="shift +1",
        pitch=60,
        transpose=1,
        expected_pitch=61,
    ),
    PulseTransposeCase(
        label="clamped at MAX_PITCH",
        pitch=MAX_PITCH,
        transpose=20,
        expected_pitch=MAX_PITCH,
    ),
    PulseTransposeCase(
        label="below A-0, the note kept",
        pitch=MIN_PITCH,
        transpose=-5,
        expected_pitch=MIN_PITCH - 5,
    ),
    PulseTransposeCase(
        label="clamped at C-0",
        pitch=MIN_PITCH,
        transpose=-20,
        expected_pitch=MIN_PLAYED_PITCH,
    ),
    PulseTransposeCase(
        label="no transpose",
        pitch=60,
        transpose=0,
        expected_pitch=60,
    ),
]


class TestPulseTranspose:
    @pytest.mark.parametrize(
        "case",
        PULSE_TRANSPOSE_CASES,
        ids=lambda c: c.label,
    )
    def test_pitch_transposed_correctly(
        self,
        case: PulseTransposeCase,
    ) -> None:
        instruction = PulseInstruction(
            on=True,
            pitch=case.pitch,
            volume=15,
            duty_cycle=0,
        )
        result = apply_modifiers(
            instruction,
            transpose=case.transpose,
            row_volume=MAX_VOLUME,
        )
        assert isinstance(result, PulseInstruction)
        assert result.pitch == case.expected_pitch


@dataclass(frozen=True, kw_only=True)
class NoiseTransposeCase(BaseTestCase):
    label: str
    period: int
    transpose: int
    expected_period: int


NOISE_TRANSPOSE_CASES = [
    NoiseTransposeCase(
        label="shift +5",
        period=3,
        transpose=5,
        expected_period=8,
    ),
    NoiseTransposeCase(
        label="wraps past 15",
        period=14,
        transpose=5,
        expected_period=3,
    ),
    NoiseTransposeCase(
        label="no transpose",
        period=7,
        transpose=0,
        expected_period=7,
    ),
    NoiseTransposeCase(
        label="negative wrap",
        period=2,
        transpose=-5,
        expected_period=13,
    ),
    NoiseTransposeCase(
        label="full wrap +16",
        period=3,
        transpose=16,
        expected_period=3,
    ),
    NoiseTransposeCase(
        label="shift to boundary",
        period=0,
        transpose=15,
        expected_period=15,
    ),
]


class TestNoiseTranspose:
    @pytest.mark.parametrize(
        "case",
        NOISE_TRANSPOSE_CASES,
        ids=lambda c: c.label,
    )
    def test_period_transposed_correctly(
        self,
        case: NoiseTransposeCase,
    ) -> None:
        instruction = NoiseInstruction(
            on=True,
            period=case.period,
            volume=15,
            short=False,
        )
        result = apply_modifiers(
            instruction,
            transpose=case.transpose,
            row_volume=MAX_VOLUME,
        )
        assert isinstance(result, NoiseInstruction)
        assert result.period == case.expected_period


@dataclass(frozen=True, kw_only=True)
class TriangleModifiersCase(BaseTestCase):
    label: str
    pitch: int
    transpose: int
    row_volume: int
    expected_pitch: int
    expected_on: bool


TRIANGLE_MODIFIERS_CASES = [
    TriangleModifiersCase(
        label="volume zero forces off",
        pitch=60,
        transpose=0,
        row_volume=0,
        expected_pitch=60,
        expected_on=False,
    ),
    TriangleModifiersCase(
        label="volume at half threshold forces off",
        pitch=60,
        transpose=0,
        row_volume=MAX_VOLUME // 2,
        expected_pitch=60,
        expected_on=False,
    ),
    TriangleModifiersCase(
        label="volume one above half threshold preserves on",
        pitch=60,
        transpose=0,
        row_volume=MAX_VOLUME // 2 + 1,
        expected_pitch=60,
        expected_on=True,
    ),
    TriangleModifiersCase(
        label="nonzero volume preserves on",
        pitch=60,
        transpose=0,
        row_volume=8,
        expected_pitch=60,
        expected_on=True,
    ),
    TriangleModifiersCase(
        label="pitch shifted by positive transpose",
        pitch=60,
        transpose=3,
        row_volume=15,
        expected_pitch=63,
        expected_on=True,
    ),
    TriangleModifiersCase(
        label="pitch shifted by negative transpose",
        pitch=60,
        transpose=-7,
        row_volume=15,
        expected_pitch=53,
        expected_on=True,
    ),
    TriangleModifiersCase(
        label="pitch clamped at MAX_PITCH",
        pitch=MAX_PITCH,
        transpose=20,
        row_volume=15,
        expected_pitch=MAX_PITCH,
        expected_on=True,
    ),
    TriangleModifiersCase(
        label="pitch clamped at C-0",
        pitch=MIN_PITCH,
        transpose=-20,
        row_volume=15,
        expected_pitch=MIN_PLAYED_PITCH,
        expected_on=True,
    ),
    TriangleModifiersCase(
        label="zero volume with pitch shift — pitch still applied",
        pitch=60,
        transpose=5,
        row_volume=0,
        expected_pitch=65,
        expected_on=False,
    ),
]


class TestTriangleModifiers:
    @pytest.mark.parametrize(
        "case",
        TRIANGLE_MODIFIERS_CASES,
        ids=lambda c: c.label,
    )
    def test_modifiers_applied(
        self,
        case: TriangleModifiersCase,
    ) -> None:
        instruction = TriangleInstruction(on=True, pitch=case.pitch)
        result = apply_modifiers(
            instruction,
            transpose=case.transpose,
            row_volume=case.row_volume,
        )
        assert isinstance(result, TriangleInstruction)
        assert result.pitch == case.expected_pitch
        assert result.on == case.expected_on


class TestTheTriangleGate:
    def test_the_triangle_sounds_at_every_level_the_gate_opens_at(self) -> None:
        """A tracker export writes the triangle's volume column by the gate, so the gate is the rule
        the song sounds the triangle by at every level a row can state.
        """
        instruction = TriangleInstruction(on=True, pitch=MIN_PITCH)
        sounded = [apply_modifiers(instruction, transpose=0, row_volume=volume).on for volume in VOLUME_RANGE]

        assert sounded == [triangle_sounds_at(volume) for volume in VOLUME_RANGE]
