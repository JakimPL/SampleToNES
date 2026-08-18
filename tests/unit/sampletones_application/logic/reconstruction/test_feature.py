from __future__ import annotations

from typing import Callable

import pytest

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction


@pytest.fixture
def reconstruction(
    reconstruction_factory: Callable[[], Reconstruction],
) -> Reconstruction:
    return reconstruction_factory()


@pytest.fixture
def feature_data(reconstruction: Reconstruction) -> FeatureData:
    return FeatureData.load(reconstruction)


class TestFeatureDataLoad:
    def test_load_creates_entry_for_each_generator(
        self,
        feature_data: FeatureData,
    ) -> None:
        assert set(feature_data.generators.keys()) == set(GeneratorName.items())

    def test_a_channel_standing_by_carries_empty_envelopes(
        self,
        reconstruction: Reconstruction,
        feature_data: FeatureData,
    ) -> None:
        """A channel the reconstruction leaves silent is loaded describing no frame."""
        standing_by = set(GeneratorName.items()) - set(reconstruction.playing_generators)
        assert standing_by
        assert all(not feature_data[generator_name].has_frames for generator_name in standing_by)

    def test_loaded_features_include_initial_pitch(
        self,
        feature_data: FeatureData,
    ) -> None:
        for features in feature_data.generators.values():
            assert features.get(FeatureKey.INITIAL_PITCH) is not None


class TestFeatureDataQueries:
    @pytest.mark.parametrize("generator_name", GeneratorName.items(), ids=lambda name: name.value)
    def test_every_channel_answers_with_its_features(
        self,
        feature_data: FeatureData,
        generator_name: GeneratorName,
    ) -> None:
        assert isinstance(feature_data[generator_name], Features)
