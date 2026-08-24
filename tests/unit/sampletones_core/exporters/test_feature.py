from typing import Optional

import numpy as np

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features, playing_channels


def build_features(frames: int, *, duty_cycle_frames: Optional[int] = None) -> Features:
    duty_cycle = None if duty_cycle_frames is None else np.zeros(duty_cycle_frames, dtype=int)
    return Features(
        initial_pitch=60,
        volume=np.full(frames, 15, dtype=int),
        arpeggio=np.zeros(frames, dtype=int),
        pitch=None,
        hi_pitch=None,
        duty_cycle=duty_cycle,
    )


class TestFrameCount:
    def test_the_longest_populated_dimension_sets_the_count(self) -> None:
        assert build_features(24, duty_cycle_frames=30).frame_count == 30

    def test_absent_dimensions_leave_the_count_to_the_others(self) -> None:
        assert build_features(24).frame_count == 24

    def test_empty_envelopes_count_no_frames(self) -> None:
        assert build_features(0).frame_count == 0


class TestHeldFeatures:
    """The dimensions an instrument leaves to the channel, read off the envelopes."""

    def test_an_instrument_writing_every_dimension_leaves_none(self) -> None:
        assert build_features(8, duty_cycle_frames=8).held_features == ()

    def test_an_empty_envelope_marks_a_dimension_the_channel_governs(self) -> None:
        features = build_features(8, duty_cycle_frames=8)
        features[FeatureKey.ARPEGGIO] = np.array([], dtype=np.int8)
        assert features.held_features == (FeatureKey.ARPEGGIO,)

    def test_a_dimension_the_channel_lacks_stays_out_of_the_listing(self) -> None:
        """The triangle channel offers no duty cycle, which is a different absence."""
        assert build_features(8).held_features == ()

    def test_leaving_a_dimension_to_the_channel_empties_its_envelope(self) -> None:
        features = build_features(8, duty_cycle_frames=8)
        features.leave_to_channel((FeatureKey.VOLUME, FeatureKey.DUTY_CYCLE))
        assert features.volume.size == 0
        assert features.duty_cycle is not None and features.duty_cycle.size == 0
        assert features.held_features == (FeatureKey.VOLUME, FeatureKey.DUTY_CYCLE)

    def test_leaving_a_dimension_the_channel_lacks_keeps_it_absent(self) -> None:
        """A record naming a duty cycle on the triangle channel leaves the channel's shape intact."""
        features = build_features(8)
        features.leave_to_channel((FeatureKey.VOLUME, FeatureKey.DUTY_CYCLE))
        assert features.duty_cycle is None
        assert features.held_features == (FeatureKey.VOLUME,)


class TestWhichChannelsSound:
    """Describing a frame is what puts a channel in play, and every reader asks the same way."""

    def test_a_channel_describing_frames_sounds(self) -> None:
        channels = {ChannelName.PULSE1: build_features(8)}

        assert playing_channels(channels) == frozenset({ChannelName.PULSE1})

    def test_a_channel_describing_nothing_stands_by(self) -> None:
        channels = {ChannelName.TRIANGLE: build_features(0)}

        assert playing_channels(channels) == frozenset()

    def test_the_channels_that_sound_are_told_from_the_ones_that_stand_by(self) -> None:
        channels = {
            ChannelName.PULSE1: build_features(8),
            ChannelName.PULSE2: build_features(0),
            ChannelName.NOISE: build_features(4),
        }

        assert playing_channels(channels) == frozenset({ChannelName.PULSE1, ChannelName.NOISE})

    def test_nothing_offered_sounds_nowhere(self) -> None:
        assert playing_channels({}) == frozenset()
