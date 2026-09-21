import numpy as np

from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor


def amplified(extractor: FeatureExtractor, fragment: Fragment, gain: float) -> Fragment:
    """The fragment played ``gain`` times as loud.

    A waveform follows the gain and the power a feature describes follows its square, so the
    feature is scaled as power through the transform, in double precision. A case reads this
    where it needs one recording louder than another, which is what a stem carrying more sound
    stands on.
    """
    power_gain = gain**2
    precision = fragment.feature.values.dtype
    feature = extractor.transformer.apply(lambda power: power * power_gain, fragment.feature.astype(np.float64))
    return Fragment(
        audio=fragment.audio * gain,
        feature=feature.astype(precision),
        windowed_audio=fragment.windowed_audio * gain,
        config=fragment.config,
    )
