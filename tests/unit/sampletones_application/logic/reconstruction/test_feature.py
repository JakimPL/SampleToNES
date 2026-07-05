from __future__ import annotations

from typing import Callable

import numpy as np
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
    def test_has_generator_for_present_generator(self, feature_data: FeatureData) -> None:
        assert feature_data.has_generator(GeneratorName.PULSE1) is True

    def test_has_generator_for_absent_generator(self, feature_data: FeatureData) -> None:
        assert feature_data.has_generator(GeneratorName.TRIANGLE) is False

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

    def test_get_feature_for_generator_returns_value_when_present(
        self,
        feature_data: FeatureData,
    ) -> None:
        result = feature_data.get_feature_for_generator(GeneratorName.PULSE1, FeatureKey.VOLUME)
        assert result is not None

    def test_get_feature_for_generator_returns_none_for_absent_generator(
        self,
        feature_data: FeatureData,
    ) -> None:
        result = feature_data.get_feature_for_generator(GeneratorName.TRIANGLE, FeatureKey.VOLUME)
        assert result is None

    def test_has_feature_for_generator_true_when_present(
        self,
        feature_data: FeatureData,
    ) -> None:
        assert feature_data.has_feature_for_generator(GeneratorName.PULSE1, FeatureKey.VOLUME) is True

    def test_has_feature_for_generator_false_for_absent_generator(
        self,
        feature_data: FeatureData,
    ) -> None:
        assert feature_data.has_feature_for_generator(GeneratorName.TRIANGLE, FeatureKey.VOLUME) is False

    def test_get_first_generator_with_feature_returns_generator(
        self,
        feature_data: FeatureData,
    ) -> None:
        result = feature_data.get_first_generator_with_feature(FeatureKey.VOLUME)
        assert result == GeneratorName.PULSE1

    def test_get_first_generator_with_feature_returns_none_when_absent(self) -> None:
        empty_data = FeatureData(
            generators={
                GeneratorName.PULSE1: Features(
                    initial_pitch=60,
                    volume=np.zeros(1, dtype=np.float32),
                    arpeggio=np.zeros(1, dtype=np.float32),
                    pitch=None,
                    hi_pitch=None,
                    duty_cycle=None,
                )
            }
        )
        result = empty_data.get_first_generator_with_feature(FeatureKey.HI_PITCH)
        assert result is None

    def test_get_generator_names_returns_all_keys(self, feature_data: FeatureData) -> None:
        names = feature_data.get_generator_names()
        assert GeneratorName.PULSE1 in names
