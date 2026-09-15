from typing import Final

import numpy as np

from sampletones_core.audio.processing import clip_audio, resample
from sampletones_shared.utils.system.modules import module_available

from .protocol import Judgment

ZIMTOHRLI_MODULE: Final[str] = "zimtohrli"
ZIMTOHRLI_REFEREE_NAME: Final[str] = "zimtohrli"
OPINION_COMPONENT: Final[str] = "mos"
SILENT_PEAK: Final[float] = 1e-9


def zimtohrli_available() -> bool:
    """Whether this interpreter carries the ``calibration`` dependency group."""
    return module_available(ZIMTOHRLI_MODULE)


class ZimtohrliReferee:
    """
    Psychoacoustic distance from the Zimtohrli auditory model, read through its Python wheel.

    The model takes 48 kHz signals in [-1, 1] and hears a full-scale sine at a fixed sound
    pressure level, so both signals share one gain bringing the reference's peak to full scale,
    the estimate is clipped to that range, and both are resampled to the model's rate. The
    wheel's ``full_scale_sine_db`` property calls a method its compiled module lacks, so the
    referee plays at the model's built-in level. The score is the Zimtohrli distance, zero for
    identical signals, and the mean opinion score the model maps it to is reported beside it.
    """

    def __init__(self, sample_rate: int) -> None:
        from zimtohrli import Pyohrli, mos_from_zimtohrli  # pylint: disable=import-error

        self.sample_rate = sample_rate
        self._model = Pyohrli()
        self._opinion = mos_from_zimtohrli
        self._model_rate = int(self._model.sample_rate)

    @property
    def name(self) -> str:
        return ZIMTOHRLI_REFEREE_NAME

    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment:
        """
        Zimtohrli distance between two equal-length signals.

        Args:
            reference: Reference waveform.
            estimate: Waveform under evaluation, of the same length.

        Returns:
            Judgment: The Zimtohrli distance, with the mean opinion score it maps to.

        Raises:
            ValueError: If the signals differ in length.
        """
        if reference.shape != estimate.shape:
            raise ValueError(f"signal shapes differ: {reference.shape} vs {estimate.shape}")

        gain = 1.0 / max(float(np.max(np.abs(reference), initial=0.0)), SILENT_PEAK)
        distance = float(
            self._model.distance(
                self._model_signal(clip_audio(reference * gain)),
                self._model_signal(clip_audio(estimate * gain)),
            )
        )
        return Judgment(
            score=distance,
            components={OPINION_COMPONENT: float(self._opinion(distance))},
        )

    def _model_signal(self, audio: np.ndarray) -> np.ndarray:
        signal: np.ndarray = resample(audio.astype(np.float32), self.sample_rate, self._model_rate)
        return signal.astype(np.float32)
