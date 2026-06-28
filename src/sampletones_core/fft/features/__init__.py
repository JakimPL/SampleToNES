from typing import Dict, Type

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod

from ..window.window import Window
from .base import FeatureExtractor
from .cqt import CqtFeatureExtractor
from .windowed import WindowedFeatureExtractor

FEATURE_EXTRACTORS: Dict[SpectrumMethod, Type[FeatureExtractor]] = {
    SpectrumMethod.FFT: WindowedFeatureExtractor,
    SpectrumMethod.LOG_SPACED_FFT: WindowedFeatureExtractor,
    SpectrumMethod.CQT: CqtFeatureExtractor,
}


def get_feature_extractor(config: Config, window: Window) -> FeatureExtractor:
    method = SpectrumMethod(config.library.spectrum_method)
    return FEATURE_EXTRACTORS[method](config, window)


__all__ = [
    "FeatureExtractor",
    "WindowedFeatureExtractor",
    "CqtFeatureExtractor",
    "FEATURE_EXTRACTORS",
    "get_feature_extractor",
]
