from dataclasses import dataclass
from typing import Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import (
    RESTING_REFERENCE_PERIOD,
    RESTING_REFERENCE_PITCH,
    supported_features,
    supports,
)
from sampletones_core.features.spec import CHANNEL_GENERATOR_KIND
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.shape import Shape
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

VOLUME: Tuple[int, ...] = (15, 12, 9, 6)
ARPEGGIO: Tuple[int, ...] = (0, 0, 12, 12)
DUTY_CYCLE: Tuple[int, ...] = (2,)


def _shape(**overrides: object) -> Shape:
    fields: dict = {
        "name": "lead",
        "envelopes": ShapeEnvelopes(volume=VOLUME, arpeggio=ARPEGGIO, duty_cycle=DUTY_CYCLE),
    }
    fields.update(overrides)
    return Shape(**fields)


class TestShapeIdentity:
    def test_each_shape_gets_its_own_id(self) -> None:
        assert _shape().id != _shape().id

    def test_clone_gets_a_fresh_id_and_carries_the_rest(self) -> None:
        shape = _shape(root_pitch=48, root_period=3, loop_point=WHOLE_LOOP_POINT)
        clone = shape.clone()

        assert clone.id != shape.id
        assert clone.name == shape.name
        assert clone.envelopes == shape.envelopes
        assert clone.root_pitch == shape.root_pitch
        assert clone.root_period == shape.root_period
        assert clone.loop_point == shape.loop_point


class TestShapeRoots:
    def test_a_shape_rests_where_a_channel_added_by_hand_rests(self) -> None:
        shape = Shape(name="lead")

        assert shape.root_pitch == RESTING_REFERENCE_PITCH
        assert shape.root_period == RESTING_REFERENCE_PERIOD

    def test_the_tonal_channels_read_the_pitch_and_noise_reads_the_period(self) -> None:
        shape = _shape(root_pitch=55, root_period=3)

        assert shape.reference(ChannelName.PULSE1) == 55
        assert shape.reference(ChannelName.PULSE2) == 55
        assert shape.reference(ChannelName.TRIANGLE) == 55
        assert shape.reference(ChannelName.NOISE) == 3


class TestShapeFeatures(BaseTestSuite):
    """One set of envelopes, read on every channel in the dimensions that channel offers."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel_name: ChannelName

    test_cases = (
        TestCase(label=ChannelName.PULSE1.value, channel_name=ChannelName.PULSE1),
        TestCase(label=ChannelName.PULSE2.value, channel_name=ChannelName.PULSE2),
        TestCase(label=ChannelName.TRIANGLE.value, channel_name=ChannelName.TRIANGLE),
        TestCase(label=ChannelName.NOISE.value, channel_name=ChannelName.NOISE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_channel_reads_the_dimensions_it_offers(self, test_case: TestCase) -> None:
        features = _shape().features(test_case.channel_name)
        kind = CHANNEL_GENERATOR_KIND[test_case.channel_name]

        assert set(features.keys()) >= set(supported_features(kind))
        assert (features.duty_cycle is not None) is supports(kind, FeatureKey.DUTY_CYCLE)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_arpeggio_is_measured_against_the_channels_root(self, test_case: TestCase) -> None:
        shape = _shape()

        assert shape.features(test_case.channel_name).initial_pitch == shape.reference(test_case.channel_name)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_channel_sounds_one_frame_per_tick(self, test_case: TestCase) -> None:
        shape = _shape()

        assert len(shape.instructions(test_case.channel_name)) == shape.envelopes.frame_count


class TestShapeInstructions:
    def test_a_pulse_frame_carries_the_volume_duty_and_root(self) -> None:
        first = _shape().instructions(ChannelName.PULSE1)[0]

        assert first == PulseInstruction(
            on=True,
            pitch=RESTING_REFERENCE_PITCH,
            volume=VOLUME[0],
            duty_cycle=DUTY_CYCLE[0],
        )

    def test_the_arpeggio_moves_the_frame_off_the_root(self) -> None:
        instructions = _shape().instructions(ChannelName.PULSE1)
        third = instructions[2]

        assert isinstance(third, PulseInstruction)
        assert third.pitch == RESTING_REFERENCE_PITCH + ARPEGGIO[2]

    def test_a_triangle_frame_sounds_at_the_root(self) -> None:
        first = _shape().instructions(ChannelName.TRIANGLE)[0]

        assert first == TriangleInstruction(on=True, pitch=RESTING_REFERENCE_PITCH)

    def test_a_noise_frame_takes_the_period_root_and_the_short_mode(self) -> None:
        first = _shape().instructions(ChannelName.NOISE)[0]

        assert first == NoiseInstruction(
            on=True,
            period=RESTING_REFERENCE_PERIOD,
            volume=VOLUME[0],
            short=True,
        )

    def test_a_shape_writing_nothing_sounds_on_no_channel(self) -> None:
        shape = Shape(name="empty")

        assert all(not shape.instructions(channel_name) for channel_name in ChannelName.items())

    def test_an_edit_reaches_the_frames(self) -> None:
        shape = _shape()
        before = shape.instructions(ChannelName.PULSE1)

        shape.envelopes = shape.envelopes.with_envelope(FeatureKey.ARPEGGIO, (7,))
        shape.invalidate()

        after = shape.instructions(ChannelName.PULSE1)
        assert after != before
        assert isinstance(after[0], PulseInstruction)
        assert after[0].pitch == RESTING_REFERENCE_PITCH + 7


class TestHeldDimensions:
    def test_an_empty_envelope_is_left_to_the_channel(self) -> None:
        shape = Shape(name="lead", envelopes=ShapeEnvelopes(arpeggio=ARPEGGIO))

        held = shape.held_features(ChannelName.PULSE1)

        assert FeatureKey.VOLUME in held
        assert FeatureKey.DUTY_CYCLE in held
        assert FeatureKey.ARPEGGIO not in held

    def test_a_channel_is_told_of_the_dimensions_it_offers_alone(self) -> None:
        shape = Shape(name="lead", envelopes=ShapeEnvelopes(arpeggio=ARPEGGIO))

        assert FeatureKey.DUTY_CYCLE not in shape.held_features(ChannelName.TRIANGLE)


class TestEnvelopeBounds:
    def test_a_volume_past_the_range_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ShapeEnvelopes(volume=(MAX_VOLUME + 1,))

    def test_a_dimension_a_shape_writes_none_of_is_refused(self) -> None:
        with pytest.raises(KeyError):
            ShapeEnvelopes().with_envelope(FeatureKey.PITCH, (1,))

    def test_the_frame_count_is_the_longest_dimension(self) -> None:
        envelopes = ShapeEnvelopes(volume=VOLUME, duty_cycle=DUTY_CYCLE)

        assert envelopes.frame_count == len(VOLUME)
