from __future__ import annotations

from typing import Callable

import pytest

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection


@pytest.fixture
def reconstruction(
    reconstruction_factory: Callable[[], Reconstruction],
) -> Reconstruction:
    return reconstruction_factory()


@pytest.fixture
def everything_heard(reconstruction: Reconstruction) -> StemSelection:
    """The reader listening to every recording on every channel, as a fresh document reads."""
    return StemSelection.everywhere(
        frozenset(reconstruction.stems_data.config.entries_by_id),
        ChannelName.items(),
    )


@pytest.fixture
def feature_data(reconstruction: Reconstruction, everything_heard: StemSelection) -> FeatureData:
    return FeatureData.heard(reconstruction, everything_heard)


class TestTheEnvelopesOfWhatIsHeard:
    def test_every_generator_answers_with_an_entry(
        self,
        feature_data: FeatureData,
    ) -> None:
        assert set(feature_data.channels.keys()) == set(ChannelName.items())

    def test_a_channel_standing_by_carries_empty_envelopes(
        self,
        reconstruction: Reconstruction,
        feature_data: FeatureData,
    ) -> None:
        """A channel the reconstruction leaves silent is loaded describing no frame."""
        standing_by = set(ChannelName.items()) - set(reconstruction.playing_channels)
        assert standing_by
        assert all(not feature_data[channel_name].has_frames for channel_name in standing_by)

    def test_the_envelopes_state_the_pitch_they_are_measured_against(
        self,
        feature_data: FeatureData,
    ) -> None:
        for features in feature_data.channels.values():
            assert features.initial_pitch is not None

    def test_hearing_every_recording_reads_the_document_itself(
        self,
        reconstruction: Reconstruction,
        feature_data: FeatureData,
    ) -> None:
        assert feature_data.channels == reconstruction.export()

    def test_a_channel_no_recording_is_heard_on_describes_no_frame(
        self,
        reconstruction: Reconstruction,
    ) -> None:
        playing = next(iter(reconstruction.playing_channels))

        feature_data = FeatureData.heard(reconstruction, StemSelection(channels={}))

        assert not feature_data[playing].has_frames


class TestFeatureDataQueries:
    @pytest.mark.parametrize("channel_name", ChannelName.items(), ids=lambda name: name.value)
    def test_every_channel_answers_with_its_features(
        self,
        feature_data: FeatureData,
        channel_name: ChannelName,
    ) -> None:
        assert isinstance(feature_data[channel_name], Features)
