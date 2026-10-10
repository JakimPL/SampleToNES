from dataclasses import dataclass
from typing import Callable, Dict, Final, Optional, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, Features, stands_by
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import sounds
from tests.conftest import ReconstructionFactory
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.long_documents import long_document

CHANNEL: Final[ChannelName] = ChannelName.PULSE1
SHORT_SECONDS: Final[float] = 1.0
LOUD: Final[int] = 9
LOOP_POINT: Final[int] = 1
Shape = Callable[[Features], Features]


@pytest.fixture
def features(reconstruction_factory: ReconstructionFactory) -> Features:
    """The envelopes a converted channel exports, which sound somewhere."""
    return reconstruction_factory().export()[CHANNEL]


@pytest.fixture(scope="module", name="converted_channels")
def converted_channels_fixture() -> Dict[ChannelName, Features]:
    """The envelopes every kind of channel exports from a short conversion sounding through every frame."""
    return long_document(SHORT_SECONDS, config=Config()).export()


class TestWhatStandsBy:
    """Envelopes are read as the rebuild a regeneration makes reads them, so the answer is the document's."""

    def test_envelopes_that_sound_keep_the_channel_in_play(self, features: Features) -> None:
        assert not stands_by(features)

    def test_envelopes_written_silent_stand_by(self, features: Features) -> None:
        silent = features.with_envelope(FeatureKey.VOLUME, Envelope[int](items=(0,) * features.frame_count))

        assert stands_by(silent)

    def test_a_held_volume_sounds(self, features: Features) -> None:
        """A volume left to the channel plays at the level a channel holds from the start of a song."""
        held = features.leave_to_channel((FeatureKey.VOLUME,))

        assert held.has_frames
        assert not stands_by(held)

    def test_envelopes_describing_no_frame_stand_by(self, features: Features) -> None:
        assert stands_by(features.leave_to_channel(features.envelopes))


def _rebuilt_frames_sound(channel_name: ChannelName, features: Features) -> bool:
    """The rebuild's own reading: whether any frame the exporter rebuilds from the envelopes is on."""
    return sounds(CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(features))


def _volume(items: Tuple[int, ...], loop_point: Optional[int] = None) -> Shape:
    def shaped(features: Features) -> Features:
        return features.with_envelope(FeatureKey.VOLUME, Envelope[int](items=items, loop_point=loop_point))

    return shaped


def _silent_throughout(features: Features) -> Features:
    return features.with_envelope(FeatureKey.VOLUME, Envelope[int](items=(0,) * features.frame_count))


def _loud_in_the_last_frame(features: Features) -> Features:
    return features.with_envelope(
        FeatureKey.VOLUME,
        Envelope[int](items=(0,) * (features.frame_count - 1) + (LOUD,)),
    )


class TestTheReadingAgreesWithTheRebuild(BaseTestSuite):
    """Reading the envelopes answers what the rebuilt frames answer, on every kind of channel.

    The rebuild is how the regeneration reads an edit; the envelopes give the same answer in one
    pass over the volume's items, which is what lets an edit's figures follow a drag frame by
    frame. A volume shorter than the frames holds its last item past its end, and a looped one
    cycles through its items, so a reading over the items alone covers every frame.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shape: Shape

    test_cases = (
        TestCase(label="as_converted", shape=lambda features: features),
        TestCase(label="volume_written_silent_throughout", shape=_silent_throughout),
        TestCase(label="loud_in_the_last_frame_alone", shape=_loud_in_the_last_frame),
        TestCase(label="a_short_volume_whose_last_item_holds_loud", shape=_volume((0, LOUD))),
        TestCase(label="a_short_volume_whose_last_item_holds_silent", shape=_volume((LOUD, 0))),
        TestCase(label="a_short_silent_volume_held", shape=_volume((0, 0))),
        TestCase(label="a_looped_volume_silent_after_its_opening", shape=_volume((LOUD, 0, 0), LOOP_POINT)),
        TestCase(label="a_looped_volume_silent_throughout", shape=_volume((0, 0, 0), LOOP_POINT)),
        TestCase(
            label="volume_left_to_the_channel", shape=lambda features: features.leave_to_channel((FeatureKey.VOLUME,))
        ),
        TestCase(label="no_frame_at_all", shape=lambda features: features.leave_to_channel(features.envelopes)),
    )

    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda channel_name: channel_name.value)
    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_envelopes_read_as_the_rebuilt_frames_do(
        self,
        test_case: TestCase,
        channel_name: ChannelName,
        converted_channels: Dict[ChannelName, Features],
    ) -> None:
        shaped = test_case.shape(converted_channels[channel_name])

        assert stands_by(shaped) == (not _rebuilt_frames_sound(channel_name, shaped))
