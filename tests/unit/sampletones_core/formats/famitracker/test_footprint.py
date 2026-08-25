from dataclasses import dataclass
from typing import Final, Optional, Sequence

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope
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
    *,
    loop_point: Optional[int] = None,
) -> Features:
    """Builds the envelopes of one channel slice, leaving the pitch dimensions unused."""

    def envelope(items: Sequence[int]) -> Envelope[int]:
        return Envelope(items=tuple(items), loop_point=loop_point if items else None)

    return Features(
        initial_pitch=REFERENCE_PITCH,
        volume=envelope(volume),
        arpeggio=envelope(arpeggio),
        pitch=None,
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else envelope(duty_cycle),
    )


class TestFeaturesFootprint(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        features: Features
        expected: InstrumentFootprint

    test_cases = (
        TestCase(
            features=build_features([15, 12, 9, 0], [0, 2, 4], [1, 1, 2]),
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=22),
            label="pulse_one_shot",
        ),
        TestCase(
            features=build_features([15, 12, 9, 0], [0, 2, 4], [1, 1, 2], loop_point=0),
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=22),
            label="pulse_loop",
        ),
        TestCase(
            features=build_features([15, 0], [0], [0]),
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=16),
            label="dimensions_of_differing_lengths",
        ),
        TestCase(
            features=build_features([15, 12, 0], [0, 1], None),
            expected=InstrumentFootprint(instrument_bytes=7, sequence_bytes=13),
            label="triangle",
        ),
        TestCase(
            features=build_features([], [], None),
            expected=InstrumentFootprint(instrument_bytes=3, sequence_bytes=0),
            label="silent",
        ),
        TestCase(
            features=build_features(
                list(range(OVER_LONG_LENGTH)),
                [0] * OVER_LONG_LENGTH,
                None,
            ),
            expected=InstrumentFootprint(instrument_bytes=7, sequence_bytes=512),
            label="capped_at_the_sequence_limit",
        ),
        TestCase(
            features=build_features(
                [0] * MAX_SEQUENCE_ITEMS,
                [0] * MAX_SEQUENCE_ITEMS,
                [0] * MAX_SEQUENCE_ITEMS,
            ),
            expected=InstrumentFootprint(instrument_bytes=9, sequence_bytes=768),
            label="largest_instrument_famitracker_holds",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_both_regions_are_measured_from_the_populated_sequences(
        self,
        test_case: TestCase,
    ) -> None:
        assert features_footprint(test_case.features) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_built_instrument_measures_the_same(self, test_case: TestCase) -> None:
        """Both entry points measure one export, so a slice reads the same either way."""
        instrument = build_instrument(0, test_case.label, test_case.features)
        assert instrument_footprint(instrument) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_total_sums_both_regions(self, test_case: TestCase) -> None:
        footprint = features_footprint(test_case.features)
        assert footprint.total_bytes == test_case.expected.instrument_bytes + test_case.expected.sequence_bytes


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
        footprints = reconstruction_footprints(sample.reconstruction)
        assert set(footprints) == {ChannelName.PULSE1, ChannelName.TRIANGLE}

    def test_a_triangle_slice_carries_one_sequence_less_than_a_pulse_slice(self) -> None:
        """Triangle exports volume and arpeggio; pulse adds duty, hence one more pointer."""
        sample = dual_generator_sample("bell", pulse_pitch=72, triangle_pitch=36)
        footprints = reconstruction_footprints(sample.reconstruction)
        pulse = footprints[ChannelName.PULSE1]
        triangle = footprints[ChannelName.TRIANGLE]
        assert pulse.instrument_bytes - triangle.instrument_bytes == SEQUENCE_POINTER_BYTES

    def test_each_channel_is_measured_as_its_own_envelopes_state_them(self) -> None:
        sample = pulse_sample("lead", pitch=60)
        features = sample.reconstruction.export()

        assert reconstruction_footprints(sample.reconstruction) == {
            channel_name: features_footprint(feature)
            for channel_name, feature in features.items()
            if feature.has_frames
        }
