from dataclasses import dataclass
from typing import Any, Callable, Final, List, Optional, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters import (
    ExporterTypeUnion,
    Features,
    NoiseExporter,
    PulseExporter,
    TriangleExporter,
)
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 4
SOUNDING_FRAMES: Final[int] = 5
OCTAVE: Final[int] = 12
PERIOD_STEP: Final[int] = 3
PULSE_VOLUME: Final[int] = 8
NOISE_VOLUME: Final[int] = 10


def _read_pitch(instruction: Any) -> int:
    pitch: int = instruction.pitch
    return pitch


def _read_period(instruction: Any) -> int:
    period: int = instruction.period
    return period


def _read_volume(instruction: Any) -> int:
    volume: int = instruction.volume
    return volume


def _read_duty_cycle(instruction: Any) -> int:
    duty_cycle: int = instruction.duty_cycle
    return duty_cycle


def _read_short(instruction: Any) -> int:
    return int(instruction.short)


def _features(
    *,
    initial_pitch: int,
    volume: Tuple[int, ...],
    arpeggio: Tuple[int, ...],
    duty_cycle: Optional[Tuple[int, ...]],
) -> Features:
    return Features(
        initial_pitch=initial_pitch,
        volume=np.array(volume, dtype=np.int8),
        arpeggio=np.array(arpeggio, dtype=np.int8),
        pitch=None,
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else np.array(duty_cycle, dtype=np.int8),
    )


def _pulse_line(pitch: int) -> List[PulseInstruction]:
    return [PulseInstruction(on=True, pitch=pitch, volume=PULSE_VOLUME, duty_cycle=0) for _ in range(SOUNDING_FRAMES)]


def _triangle_line(pitch: int) -> List[TriangleInstruction]:
    return [TriangleInstruction(on=True, pitch=pitch) for _ in range(SOUNDING_FRAMES)]


def _noise_line(period: int) -> List[NoiseInstruction]:
    return [NoiseInstruction(on=True, period=period, volume=NOISE_VOLUME, short=False) for _ in range(SOUNDING_FRAMES)]


class TestArpeggioReferenceStability(BaseTestSuite):
    """The reference pitch an arpeggio is measured against holds across an edit to the envelope.

    Each case walks the sequence a user performs in the instruments panel: a flat contour is
    anchored once, an arpeggio envelope is typed in, the channel is rebuilt and exported again
    against the stored anchor, and the envelope is finally cleared. The last step is the guard —
    clearing the envelope returns every frame to the reference it started from, including the
    frames the envelope is too short to cover.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: int
        exporter: ExporterTypeUnion
        instructions: Sequence[InstructionUnion]
        read_pitch: Callable[[Any], int]
        arpeggio: np.ndarray
        edited_pitches: List[int]

    test_cases = (
        TestCase(
            label="pulse",
            exporter=PulseExporter,
            instructions=_pulse_line(REFERENCE_PITCH),
            read_pitch=_read_pitch,
            arpeggio=np.array([OCTAVE, 0], dtype=np.int8),
            edited_pitches=[REFERENCE_PITCH + OCTAVE] + [REFERENCE_PITCH] * SOUNDING_FRAMES,
            expected=REFERENCE_PITCH,
        ),
        TestCase(
            label="triangle",
            exporter=TriangleExporter,
            instructions=_triangle_line(REFERENCE_PITCH),
            read_pitch=_read_pitch,
            arpeggio=np.array([OCTAVE, 0], dtype=np.int8),
            edited_pitches=[REFERENCE_PITCH + OCTAVE] + [REFERENCE_PITCH] * SOUNDING_FRAMES,
            expected=REFERENCE_PITCH,
        ),
        TestCase(
            label="noise",
            exporter=NoiseExporter,
            instructions=_noise_line(REFERENCE_PERIOD),
            read_pitch=_read_period,
            arpeggio=np.array([PERIOD_STEP, 0], dtype=np.int8),
            edited_pitches=[REFERENCE_PERIOD + PERIOD_STEP] + [REFERENCE_PERIOD] * SOUNDING_FRAMES,
            expected=REFERENCE_PERIOD,
        ),
    )

    @staticmethod
    def _export(test_case: TestCase, instructions: Sequence[InstructionUnion]) -> Features:
        return test_case.exporter().to_features(
            list(instructions),
            test_case.expected,
            (),
        )

    @classmethod
    def _edited(cls, test_case: TestCase) -> List[InstructionUnion]:
        features = cls._export(test_case, test_case.instructions)
        features[FeatureKey.ARPEGGIO] = test_case.arpeggio
        return test_case.exporter.from_features(features)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_derived_reference_is_the_contour_pitch(self, test_case: TestCase) -> None:
        assert test_case.exporter.derive_initial_pitch(list(test_case.instructions)) == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_flat_contour_exports_a_zero_offset(self, test_case: TestCase) -> None:
        features = self._export(test_case, test_case.instructions)

        assert features.initial_pitch == test_case.expected
        assert features.arpeggio.tolist() == [0]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_edited_arpeggio_offsets_every_frame_from_the_reference(self, test_case: TestCase) -> None:
        """The envelope's final value carries over the frames beyond it, as an offset.

        A two-item envelope describes a channel that sounds for longer, so the frames past
        its end repeat its last offset. They land on the reference, rather than accumulating
        a step per frame.
        """
        instructions = self._edited(test_case)

        assert [test_case.read_pitch(instruction) for instruction in instructions] == test_case.edited_pitches

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_re_export_keeps_the_stored_reference(self, test_case: TestCase) -> None:
        features = self._export(test_case, self._edited(test_case))

        assert features.initial_pitch == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_re_export_reads_the_edited_arpeggio_back(self, test_case: TestCase) -> None:
        features = self._export(test_case, self._edited(test_case))

        assert features.arpeggio.tolist() == test_case.arpeggio.tolist()

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_cleared_arpeggio_returns_every_frame_to_the_reference(self, test_case: TestCase) -> None:
        """Clearing an arpeggio envelope restores the pitch the channel started at.

        This is the reported behaviour: typing ``12 0`` and then clearing it back to ``0``
        sounds the sample at the note it was reconstructed at.
        """
        features = self._export(test_case, self._edited(test_case))
        features[FeatureKey.ARPEGGIO] = np.zeros(len(test_case.arpeggio), dtype=np.int8)

        cleared = test_case.exporter.from_features(features)

        pitches = [test_case.read_pitch(instruction) for instruction in cleared]
        assert pitches == [test_case.expected] * len(cleared)
        assert len(cleared) == len(test_case.edited_pitches)


class TestAbsentArpeggioEnvelope(BaseTestSuite):
    """An arpeggio envelope covering no frame sounds the whole sequence at its reference pitch."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: int
        exporter: ExporterTypeUnion
        features: Features
        read_pitch: Callable[[Any], int]

    test_cases = (
        TestCase(
            label="pulse",
            exporter=PulseExporter,
            features=Features(
                initial_pitch=REFERENCE_PITCH,
                volume=np.array([PULSE_VOLUME, PULSE_VOLUME, 0], dtype=np.int8),
                arpeggio=np.array([], dtype=np.int8),
                pitch=None,
                hi_pitch=None,
                duty_cycle=np.array([0], dtype=np.int8),
            ),
            read_pitch=_read_pitch,
            expected=REFERENCE_PITCH,
        ),
        TestCase(
            label="triangle",
            exporter=TriangleExporter,
            features=Features(
                initial_pitch=REFERENCE_PITCH,
                volume=np.array([15, 15, 0], dtype=np.int8),
                arpeggio=np.array([], dtype=np.int8),
                pitch=None,
                hi_pitch=None,
                duty_cycle=None,
            ),
            read_pitch=_read_pitch,
            expected=REFERENCE_PITCH,
        ),
        TestCase(
            label="noise",
            exporter=NoiseExporter,
            features=Features(
                initial_pitch=REFERENCE_PERIOD,
                volume=np.array([NOISE_VOLUME, NOISE_VOLUME, 0], dtype=np.int8),
                arpeggio=np.array([], dtype=np.int8),
                pitch=None,
                hi_pitch=None,
                duty_cycle=np.array([0], dtype=np.int8),
            ),
            read_pitch=_read_period,
            expected=REFERENCE_PERIOD,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_every_frame_sounds_at_the_reference(self, test_case: TestCase) -> None:
        instructions = test_case.exporter.from_features(test_case.features)

        pitches = [test_case.read_pitch(instruction) for instruction in instructions]
        assert pitches == [test_case.expected] * len(test_case.features.volume)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_audible_frames_stay_audible(self, test_case: TestCase) -> None:
        instructions = test_case.exporter.from_features(test_case.features)

        assert instructions[0].on is True
        assert instructions[-1].on is False


class TestChannelHeldDimensions(BaseTestSuite):
    """A dimension left to the channel sounds at the value a channel holds from a song's start.

    An instruction states every dimension of its frame, so rebuilding a sequence from envelopes
    that leave one out still has to state it. The value stated is the channel's own — full volume,
    no arpeggio offset, the first timbre — which is what the instrument sounds like played alone.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        exporter: ExporterTypeUnion
        features: Features
        read_value: Callable[[Any], int]
        expected: int

    test_cases = (
        TestCase(
            label="pulse_volume",
            exporter=PulseExporter,
            features=_features(
                initial_pitch=REFERENCE_PITCH,
                volume=(),
                arpeggio=(0, 0, 0),
                duty_cycle=(1,),
            ),
            read_value=_read_volume,
            expected=MAX_VOLUME,
        ),
        TestCase(
            label="pulse_duty_cycle",
            exporter=PulseExporter,
            features=_features(
                initial_pitch=REFERENCE_PITCH,
                volume=(PULSE_VOLUME, PULSE_VOLUME, 0),
                arpeggio=(0,),
                duty_cycle=(),
            ),
            read_value=_read_duty_cycle,
            expected=0,
        ),
        TestCase(
            label="noise_volume",
            exporter=NoiseExporter,
            features=_features(
                initial_pitch=REFERENCE_PERIOD,
                volume=(),
                arpeggio=(0, 0, 0),
                duty_cycle=(0,),
            ),
            read_value=_read_volume,
            expected=MAX_VOLUME,
        ),
        TestCase(
            label="noise_mode",
            exporter=NoiseExporter,
            features=_features(
                initial_pitch=REFERENCE_PERIOD,
                volume=(NOISE_VOLUME, NOISE_VOLUME, 0),
                arpeggio=(0,),
                duty_cycle=(),
            ),
            read_value=_read_short,
            expected=0,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_every_frame_states_the_value_the_channel_holds(self, test_case: TestCase) -> None:
        instructions = test_case.exporter.from_features(test_case.features)

        assert [test_case.read_value(instruction) for instruction in instructions] == [test_case.expected] * len(
            instructions
        )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_written_dimensions_set_the_frame_count(self, test_case: TestCase) -> None:
        instructions = test_case.exporter.from_features(test_case.features)

        assert len(instructions) == test_case.features.frame_count


class TestHeldDimensionRoundTrip:
    """A dimension the channel governs comes back empty, telling it apart from one holding a zero."""

    def test_a_held_dimension_comes_back_empty(self) -> None:
        features = _features(
            initial_pitch=REFERENCE_PITCH,
            volume=(PULSE_VOLUME, PULSE_VOLUME, 0),
            arpeggio=(),
            duty_cycle=(1,),
        )
        instructions = PulseExporter.from_features(features)

        exported = PulseExporter().to_features(
            instructions,
            REFERENCE_PITCH,
            features.held_features,
        )

        assert exported.arpeggio.size == 0
        assert exported.held_features == (FeatureKey.ARPEGGIO,)

    def test_a_written_dimension_comes_back_with_its_items(self) -> None:
        features = _features(
            initial_pitch=REFERENCE_PITCH,
            volume=(PULSE_VOLUME, PULSE_VOLUME, 0),
            arpeggio=(),
            duty_cycle=(1,),
        )
        instructions = PulseExporter.from_features(features)

        exported = PulseExporter().to_features(
            instructions,
            REFERENCE_PITCH,
            features.held_features,
        )

        assert exported.volume.tolist() == [PULSE_VOLUME, PULSE_VOLUME, 0]
        assert exported.duty_cycle is not None
        assert exported.duty_cycle.tolist() == [1]

    def test_an_instrument_holding_every_dimension_describes_no_frame(self) -> None:
        features = _features(
            initial_pitch=REFERENCE_PITCH,
            volume=(),
            arpeggio=(),
            duty_cycle=(),
        )

        assert PulseExporter.from_features(features) == []
