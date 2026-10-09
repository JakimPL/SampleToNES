from typing import Final

import pytest

from sampletones_application.logic.reconstruction.rewrites.steps import ChannelChange
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.reconstructions import Reconstruction
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, taking_turns

__all__ = ["taking_turns"]

FIRST_VOLUME: Final[Envelope[int]] = Envelope[int](items=(5, 5))
LATER_VOLUME: Final[Envelope[int]] = Envelope[int](items=(3, 3))
ARPEGGIO: Final[Envelope[int]] = Envelope[int](items=(0, 3), loop_point=1)
FIRST_PITCH: Final[int] = 62
LATER_PITCH: Final[int] = 64


def _change(
    channel_name: ChannelName,
    feature_key: FeatureKey,
    envelope: Envelope[int],
) -> ChannelChange:
    return ChannelChange(
        channel_name=channel_name,
        feature_key=feature_key,
        envelopes={feature_key: envelope},
        initial_pitch=None,
    )


def _pitch(value: int) -> ChannelChange:
    return ChannelChange(
        channel_name=SHARED_CHANNEL,
        feature_key=FeatureKey.INITIAL_PITCH,
        envelopes={},
        initial_pitch=value,
    )


@pytest.fixture
def features(taking_turns: Reconstruction) -> Features:
    """The shared channel's envelopes as the document holds them."""
    return taking_turns.export()[SHARED_CHANNEL]


class TestMergingTwoChanges:
    """Two changes of one channel make one, carrying what both moved, the later winning where both moved."""

    def test_the_later_value_of_a_dimension_wins(self) -> None:
        merged = _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).merged(
            _change(SHARED_CHANNEL, FeatureKey.VOLUME, LATER_VOLUME)
        )

        assert merged.envelopes == {FeatureKey.VOLUME: LATER_VOLUME}

    def test_dimensions_moved_apart_are_both_carried(self) -> None:
        merged = _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).merged(
            _change(SHARED_CHANNEL, FeatureKey.ARPEGGIO, ARPEGGIO)
        )

        assert merged.envelopes == {FeatureKey.VOLUME: FIRST_VOLUME, FeatureKey.ARPEGGIO: ARPEGGIO}

    def test_the_dimension_moved_last_names_the_change(self) -> None:
        merged = _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).merged(
            _change(SHARED_CHANNEL, FeatureKey.ARPEGGIO, ARPEGGIO)
        )

        assert merged.feature_key is FeatureKey.ARPEGGIO

    def test_a_later_pitch_wins(self) -> None:
        assert _pitch(FIRST_PITCH).merged(_pitch(LATER_PITCH)).initial_pitch == LATER_PITCH

    def test_a_pitch_stands_through_a_later_change_that_leaves_it(self) -> None:
        merged = _pitch(FIRST_PITCH).merged(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))

        assert merged.initial_pitch == FIRST_PITCH
        assert merged.envelopes == {FeatureKey.VOLUME: FIRST_VOLUME}

    def test_a_change_of_another_channel_is_refused(self) -> None:
        with pytest.raises(ValueError, match="merges into a change of that channel alone"):
            _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).merged(
                _change(SOLE_CHANNEL, FeatureKey.VOLUME, LATER_VOLUME)
            )


class TestWritingAChangeOverTheDocument:
    """A change writes what the reader moved over the envelopes the document holds at its turn."""

    def test_a_moved_dimension_takes_the_readers_value(self, features: Features) -> None:
        rebased = _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).rebased(features)

        assert rebased.volume == FIRST_VOLUME

    def test_the_dimensions_left_alone_are_read_from_the_document(self, features: Features) -> None:
        document = features.with_envelope(FeatureKey.ARPEGGIO, ARPEGGIO)

        rebased = _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).rebased(document)

        assert rebased.arpeggio == ARPEGGIO
        assert rebased.duty_cycle == document.duty_cycle
        assert rebased.initial_pitch == document.initial_pitch

    def test_a_moved_pitch_is_written(self, features: Features) -> None:
        rebased = _pitch(LATER_PITCH).rebased(features)

        assert rebased.initial_pitch == LATER_PITCH
        assert rebased.envelopes == features.envelopes

    def test_a_merged_change_writes_what_both_moved(self, features: Features) -> None:
        merged = _change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME).merged(_pitch(LATER_PITCH))

        rebased = merged.rebased(features)

        assert rebased.volume == FIRST_VOLUME
        assert rebased.initial_pitch == LATER_PITCH
