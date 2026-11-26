from typing import Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.fft.fragment.stacked import StackedFeature
from sampletones_core.fft.layers import LIBRARY_WEIGHT, analysis_layers, read_frames
from sampletones_core.structures.histogram import Histogram
from tests.suite.base import BaseTestSuite

ADDED_WEIGHT: Final[float] = 0.5
FRAMES: Final[int] = 12
SEED: Final[int] = 0


def _layered() -> Config:
    return Config.model_validate(
        {"generation": {"layers": [{"method": SpectrumMethod.LOG_SPACED_FFT.value, "weight": ADDED_WEIGHT}]}}
    )


@pytest.fixture(name="audio", scope="module")
def audio_fixture() -> np.ndarray:
    frame_length = Config().library.frame_length
    return (0.1 * np.random.default_rng(SEED).standard_normal(FRAMES * frame_length)).astype(np.float32)


class TestTheAnalysisLayers(BaseTestSuite):
    """The library's own spectrum method first, at weight one, then each method the configuration adds."""

    def test_a_configuration_adding_no_layer_reads_its_library_s_method_alone(self) -> None:
        (layer,) = analysis_layers(Config())

        assert (layer.config.library, layer.weight) == (Config().library, LIBRARY_WEIGHT)

    def test_each_added_method_follows_the_library_s_own_at_its_weight(self) -> None:
        config = _layered()

        layers = analysis_layers(config)

        assert [(layer.config.library.spectrum_method, layer.weight) for layer in layers] == [
            (config.library.spectrum_method, LIBRARY_WEIGHT),
            (SpectrumMethod.LOG_SPACED_FFT, ADDED_WEIGHT),
        ]

    def test_a_layer_reads_one_method_and_keeps_every_other_library_setting(self) -> None:
        config = _layered()

        for layer in analysis_layers(config):
            assert not layer.config.generation.layers
            assert layer.config.library.model_copy(update={"spectrum_method": config.library.spectrum_method}) == (
                config.library
            )


class TestReadingFrames(BaseTestSuite):
    """A frame holds one method's histogram, or every layer's bins stacked in order."""

    def test_a_frame_read_by_one_method_holds_its_histogram(self, audio: np.ndarray) -> None:
        config = Config()
        window = Window.from_config(config)

        frames = read_frames(audio, config, window)

        alone = get_feature_extractor(config, window).extract(audio)
        assert all(isinstance(frame.feature, Histogram) for frame in frames)
        assert all(np.array_equal(frame.feature.values, other.feature.values) for frame, other in zip(frames, alone))

    def test_a_frame_read_by_several_methods_stacks_each_method_s_reading(self, audio: np.ndarray) -> None:
        config = _layered()

        frames = read_frames(audio, config, Window.from_config(config))

        readings: List[List[np.ndarray]] = [
            [np.asarray(frame.feature.values) for frame in layer.extractor.extract(audio)]
            for layer in analysis_layers(config)
        ]
        assert len(frames) == FRAMES
        for index, frame in enumerate(frames):
            assert isinstance(frame.feature, StackedFeature)
            assert np.array_equal(frame.feature.values, np.concatenate([reading[index] for reading in readings]))
