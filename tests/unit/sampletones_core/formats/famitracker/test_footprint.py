from dataclasses import dataclass
from typing import Final, Optional, Sequence

import numpy as np
import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.feature import Features
from sampletones_core.formats.famitracker.builder import build_instrument
from sampletones_core.formats.famitracker.footprint import (
    InstrumentFootprint,
    features_footprint,
    instrument_footprint,
    reconstruction_footprints,
    sequence_footprint,
    sequences_footprint,
    total_footprint,
)
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.memory import (
    INSTRUMENT_DEFINITION_BYTES,
    SEQUENCE_HEADER_BYTES,
    SEQUENCE_POINTER_BYTES,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
    SequenceKind,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conftest import dual_generator_sample, pulse_sample

REFERENCE_PITCH: Final[int] = 60
OVER_LONG_LENGTH: Final[int] = MAX_SEQUENCE_ITEMS + 48


def build_features(
    volume: Sequence[int],
    arpeggio: Sequence[int],
    duty_cycle: Optional[Sequence[int]],
) -> Features:
    """Builds the envelopes of one generator slice, leaving the pitch dimensions unused."""
    return Features(
        initial_pitch=REFERENCE_PITCH,
        volume=np.array(volume, dtype=int),
        arpeggio=np.array(arpeggio, dtype=int),
        pitch=None,
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else np.array(duty_cycle, dtype=int),
    )


class TestFeaturesFootprint(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class FootprintCase(BaseRegularTestCase):
        features: Features
        loop: bool
        expected: InstrumentFootprint

    test_cases = (
        FootprintCase(
            features=build_features([15, 12, 9, 0], [0, 2, 4], [1, 1, 2]),
            loop=False,
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=22),
            label="pulse_one_shot",
        ),
        FootprintCase(
            features=build_features([15, 12, 9, 0], [0, 2, 4], [1, 1, 2]),
            loop=True,
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=21),
            label="pulse_loop",
        ),
        FootprintCase(
            features=build_features([15, 0], [0], [0]),
            loop=False,
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=16),
            label="dimensions_of_differing_lengths",
        ),
        FootprintCase(
            features=build_features([15, 12, 0], [0, 1], None),
            loop=False,
            expected=InstrumentFootprint(instrument_bytes=7, sequence_bytes=13),
            label="triangle",
        ),
        FootprintCase(
            features=build_features([], [], None),
            loop=False,
            expected=InstrumentFootprint(instrument_bytes=3, sequence_bytes=0),
            label="silent",
        ),
        FootprintCase(
            features=build_features(
                list(range(OVER_LONG_LENGTH)),
                [0] * OVER_LONG_LENGTH,
                None,
            ),
            loop=False,
            expected=InstrumentFootprint(instrument_bytes=7, sequence_bytes=512),
            label="capped_at_the_sequence_limit",
        ),
        FootprintCase(
            features=build_features(
                [0] * MAX_SEQUENCE_ITEMS,
                [0] * MAX_SEQUENCE_ITEMS,
                [0] * MAX_SEQUENCE_ITEMS,
            ),
            loop=False,
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=768),
            label="largest_instrument_famitracker_holds",
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_both_regions_are_measured_from_the_populated_sequences(
        self,
        case: FootprintCase,
    ) -> None:
        assert features_footprint(case.features, loop=case.loop) == case.expected

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_built_instrument_measures_the_same(self, case: FootprintCase) -> None:
        """Both entry points measure one export, so a slice reads the same either way."""
        instrument = build_instrument(0, case.label, case.features, loop=case.loop)
        assert instrument_footprint(instrument) == case.expected

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_total_sums_both_regions(self, case: FootprintCase) -> None:
        footprint = features_footprint(case.features, loop=case.loop)
        assert footprint.total_bytes == case.expected.instrument_bytes + case.expected.sequence_bytes


class TestSequenceFootprint:
    def test_a_sequence_holds_its_header_and_one_byte_per_item(self) -> None:
        sequence = InstrumentSequence(kind=SequenceKind.VOLUME, items=(15, 12, 9))
        assert sequence_footprint(sequence) == SEQUENCE_HEADER_BYTES + 3

    def test_a_disabled_sequence_costs_nothing(self) -> None:
        sequences = (
            InstrumentSequence(kind=SequenceKind.VOLUME, items=(15, 12)),
            InstrumentSequence(kind=SequenceKind.PITCH, items=()),
        )
        footprint = sequences_footprint(sequences)
        assert footprint.instrument_bytes == INSTRUMENT_DEFINITION_BYTES + SEQUENCE_POINTER_BYTES
        assert footprint.sequence_bytes == SEQUENCE_HEADER_BYTES + 2


class TestTotalFootprint:
    def test_regions_are_summed_separately(self) -> None:
        footprints = (
            InstrumentFootprint(instrument_bytes=9, sequence_bytes=24),
            InstrumentFootprint(instrument_bytes=7, sequence_bytes=16),
        )
        assert total_footprint(footprints) == InstrumentFootprint(instrument_bytes=16, sequence_bytes=40)

    def test_no_instruments_cost_nothing(self) -> None:
        assert total_footprint(()) == InstrumentFootprint(instrument_bytes=0, sequence_bytes=0)


class TestReconstructionFootprints:
    def test_one_entry_per_playing_channel(self) -> None:
        """The sample holds every channel; the two that play are the two an export writes."""
        sample = dual_generator_sample("bell", pulse_pitch=72, triangle_pitch=36)
        footprints = reconstruction_footprints(sample.reconstruction, loop=sample.loop)
        assert set(footprints) == {GeneratorName.PULSE1, GeneratorName.TRIANGLE}

    def test_a_triangle_slice_carries_one_sequence_less_than_a_pulse_slice(self) -> None:
        """Triangle exports volume and arpeggio; pulse adds duty, hence one more pointer."""
        sample = dual_generator_sample("bell", pulse_pitch=72, triangle_pitch=36)
        footprints = reconstruction_footprints(sample.reconstruction, loop=sample.loop)
        pulse = footprints[GeneratorName.PULSE1]
        triangle = footprints[GeneratorName.TRIANGLE]
        assert pulse.instrument_bytes - triangle.instrument_bytes == SEQUENCE_POINTER_BYTES

    def test_each_channel_is_measured_under_the_given_loop_flag(self) -> None:
        sample = pulse_sample("lead", pitch=60)
        features = sample.reconstruction.export()
        for loop in (False, True):
            assert reconstruction_footprints(sample.reconstruction, loop=loop) == {
                generator_name: features_footprint(feature, loop=loop)
                for generator_name, feature in features.items()
                if feature.has_frames
            }

    def test_looping_costs_the_shortest_dimensions_length(self) -> None:
        """A looping instrument shares the shortest dimension's length, so it stores fewer items."""
        sample = pulse_sample("lead", pitch=60)
        one_shot = total_footprint(reconstruction_footprints(sample.reconstruction, loop=False).values())
        looping = total_footprint(reconstruction_footprints(sample.reconstruction, loop=True).values())
        assert one_shot.instrument_bytes == looping.instrument_bytes
        assert looping.sequence_bytes < one_shot.sequence_bytes
