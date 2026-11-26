from dataclasses import dataclass
from functools import cached_property
from typing import Final, List, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod

from .features import FeatureExtractor, get_feature_extractor
from .fragment.fragment import Fragment
from .fragment.stacked import StackedFeature
from .window.window import Window

LIBRARY_WEIGHT: Final[float] = 1.0


@dataclass(frozen=True)
class AnalysisLayer:
    """One spectrum method a conversion reads its frames with.

    A conversion reads every frame with its library's spectrum method, and with each method its
    ``generation.layers`` add. A layer stands for one of them: the conversion's configuration with
    the library's method set to the layer's, which selects the layer's window, extractor and library,
    the criterion's weights on its bins and the window model's profiles of them.

    Attributes:
        config: The conversion's configuration reading with the layer's method alone.
        weight: The weight the layer's reading holds in the criterion, ``LIBRARY_WEIGHT`` for the
            library's own method.
    """

    config: Config
    weight: float

    @cached_property
    def window(self) -> Window:
        """The analysis window the layer's method reads a frame through."""
        return Window.from_config(self.config)

    @cached_property
    def extractor(self) -> FeatureExtractor:
        """The extractor reading a frame with the layer's method."""
        return get_feature_extractor(self.config, self.window)


def analysis_layers(config: Config) -> Tuple[AnalysisLayer, ...]:
    """Every spectrum method a conversion under ``config`` reads its frames with, the library's own first."""
    library = AnalysisLayer(config=layer_config(config, config.library.spectrum_method), weight=LIBRARY_WEIGHT)
    added = (
        AnalysisLayer(config=layer_config(config, layer.method), weight=layer.weight)
        for layer in config.generation.layers
    )
    return (library, *added)


def layer_config(config: Config, method: SpectrumMethod) -> Config:
    """``config`` reading the frames with ``method`` alone: the library's method set to it, and no layer added."""
    library = config.library.model_copy(update={"spectrum_method": method})
    generation = config.generation.model_copy(update={"layers": ()})
    return config.model_copy(update={"library": library, "generation": generation})


def read_frames(audio: np.ndarray, config: Config, window: Window) -> List[Fragment]:
    """Every whole frame of ``audio``, read with each spectrum method a conversion under ``config`` reads.

    A frame read by the library's method alone holds that method's histogram, read through
    ``window``. A frame read by several methods holds their bins stacked (``StackedFeature``), each
    read through its own layer's window, and keeps its own stretch of the audio.
    """
    layers = analysis_layers(config)
    if len(layers) == 1:
        return get_feature_extractor(config, window).extract(audio)

    readings = [layer.extractor.extract(audio) for layer in layers]
    return [
        Fragment(
            audio=frames[0].audio,
            feature=StackedFeature(layers=tuple(frame.feature for frame in frames)),
            config=config,
        )
        for frames in zip(*readings)
    ]
