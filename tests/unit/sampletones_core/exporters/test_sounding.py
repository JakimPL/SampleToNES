from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features, stands_by
from sampletones_core.features.envelope import Envelope
from tests.conftest import ReconstructionFactory

CHANNEL: Final[ChannelName] = ChannelName.PULSE1


@pytest.fixture
def features(reconstruction_factory: ReconstructionFactory) -> Features:
    """The envelopes a converted channel exports, which sound somewhere."""
    return reconstruction_factory().export()[CHANNEL]


class TestWhatStandsBy:
    """Envelopes are read through the rebuild a regeneration makes, so the answer is the document's."""

    def test_envelopes_that_sound_keep_the_channel_in_play(self, features: Features) -> None:
        assert not stands_by(CHANNEL, features)

    def test_envelopes_written_silent_stand_by(self, features: Features) -> None:
        silent = features.with_envelope(FeatureKey.VOLUME, Envelope[int](items=(0,) * features.frame_count))

        assert stands_by(CHANNEL, silent)

    def test_a_held_volume_sounds(self, features: Features) -> None:
        """A volume left to the channel plays at the level a channel holds from the start of a song."""
        held = features.leave_to_channel((FeatureKey.VOLUME,))

        assert held.has_frames
        assert not stands_by(CHANNEL, held)

    def test_envelopes_describing_no_frame_stand_by(self, features: Features) -> None:
        assert stands_by(CHANNEL, features.leave_to_channel(features.envelopes))
