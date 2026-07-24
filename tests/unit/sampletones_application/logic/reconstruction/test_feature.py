from __future__ import annotations

from typing import Callable

import pytest

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction


@pytest.fixture
def reconstruction(reconstruction_factory: Callable[[], Reconstruction]) -> Reconstruction:
    return reconstruction_factory()


@pytest.fixture
def feature_data(reconstruction: Reconstruction) -> FeatureData:
    return FeatureData.load(reconstruction)


class TestFeatureDataLoad:
    def test_load_creates_entry_for_each_generator(
        self,
        reconstruction: Reconstruction,
        feature_data: FeatureData,
    ) -> None:
        assert set(feature_data.generators.keys()) == set(reconstruction.approximations.keys())

    def test_loaded_features_include_initial_pitch(
        self,
        feature_data: FeatureData,
    ) -> None:
        for features in feature_data.generators.values():
            assert features.get(FeatureKey.INITIAL_PITCH) is not None


class TestFeatureDataQueries:
    def test_get_generator_features_returns_features_for_present(
        self,
        feature_data: FeatureData,
    ) -> None:
        result = feature_data.get_generator_features(GeneratorName.PULSE1)
        assert isinstance(result, Features)

    def test_get_generator_features_returns_none_for_absent(
        self,
        feature_data: FeatureData,
    ) -> None:
        assert feature_data.get_generator_features(GeneratorName.TRIANGLE) is None
