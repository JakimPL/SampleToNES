from typing import Dict, Type

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod

from ..window.window import Window
from .base import FeatureExtractor
from .cqt import CQTFeatureExtractor
from .windowed import WindowedFeatureExtractor

FEATURE_EXTRACTORS: Dict[SpectrumMethod, Type[FeatureExtractor]] = {
    SpectrumMethod.FFT: WindowedFeatureExtractor,
    SpectrumMethod.LOG_SPACED_FFT: WindowedFeatureExtractor,
    SpectrumMethod.CQT: CQTFeatureExtractor,
}


def get_feature_extractor(config: Config, window: Window) -> FeatureExtractor:
    method = SpectrumMethod(config.library.spectrum_method)
    return FEATURE_EXTRACTORS[method](config, window)


__all__ = [
    "FEATURE_EXTRACTORS",
    "CQTFeatureExtractor",
    "FeatureExtractor",
    "WindowedFeatureExtractor",
    "get_feature_extractor",
]
