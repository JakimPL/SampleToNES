import math
from typing import Dict, Final, List

import numpy as np

from sampletones_tools.calibration.config.referee import RefereeConfig

from .protocol import Judgment

CONTOUR_REFEREE: Final[str] = "contour"
SPREAD: Final[str] = "spread"
ONSET: Final[str] = "onset"
BAND_PREFIX: Final[str] = "band-"
LEVEL_FLOOR: Final[float] = 1e-12
DECIBELS_PER_POWER_DECADE: Final[float] = 10.0
LOW_PERCENTILE: Final[float] = 10.0
HIGH_PERCENTILE: Final[float] = 90.0
OCTAVE_HALF_WIDTH: Final[float] = math.sqrt(2.0)


class ContourReferee:
    """Reads whether a render follows its recording's loudness over time and over the bands of the spectrum.

    Both signals are cut into short frames, each measured as its level in decibels. Over the frames
    the recording sounds in, the score is how far the render's levels stray from the recording's
    once their difference is centered: zero for a render that rises and falls exactly as the
    recording does, at any constant offset. The readings behind it:

    - ``spread``: the range of the render's levels less the recording's, the 10th to 90th percentile,
      so a render whose dynamics flatten reads below zero;
    - ``onset``: how much louder the render plays than the recording in the first frames after each
      silence, so a render that overshoots its attacks reads above zero;
    - ``band-F``: the render's energy less the recording's in the octave band centered on ``F`` hertz,
      over the bands the recording fills, so an implied equalization reads as a curve.
    """

    def __init__(self, sample_rate: int, *, config: RefereeConfig) -> None:
        self._sample_rate = sample_rate
        self._frame_length = round(sample_rate / config.contour_frame_rate)
        self._audible_decibels = config.contour_audible_decibels
        self._onset_frames = config.contour_onset_frames
        self._bands = config.contour_band_centers
        self._band_floor_decibels = config.contour_band_floor_decibels

    @property
    def name(self) -> str:
        return CONTOUR_REFEREE

    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment:
        """How closely ``estimate`` follows the loudness of ``reference`` over time and over the bands."""
        written, played = self._levels(reference), self._levels(estimate)
        audible = written > np.max(written) - self._audible_decibels
        difference = played[audible] - written[audible]
        components: Dict[str, float] = {
            SPREAD: _spread(played[audible]) - _spread(written[audible]),
            ONSET: self._onset(written, played, audible),
            **self._band_balance(reference, estimate),
        }
        return Judgment(score=float(np.std(difference)), components=components)

    def _levels(self, audio: np.ndarray) -> np.ndarray:
        frames = len(audio) // self._frame_length
        cut = np.asarray(audio[: frames * self._frame_length], dtype=np.float64).reshape(frames, self._frame_length)
        levels = DECIBELS_PER_POWER_DECADE * np.log10(np.mean(np.square(cut), axis=1) + LEVEL_FLOOR)
        return np.asarray(levels, dtype=np.float64)

    def _onset(self, written: np.ndarray, played: np.ndarray, audible: np.ndarray) -> float:
        starts = [frame for frame in range(len(audible)) if audible[frame] and (frame == 0 or not audible[frame - 1])]
        if not starts:
            return 0.0

        rises: List[float] = []
        for start in starts:
            span = slice(start, min(start + self._onset_frames, len(written)))
            rises.append(float(np.mean(played[span] - written[span])))

        return float(np.mean(rises))

    def _band_balance(self, reference: np.ndarray, estimate: np.ndarray) -> Dict[str, float]:
        frequencies = np.fft.rfftfreq(len(reference), d=1.0 / self._sample_rate)
        written = np.abs(np.fft.rfft(reference)) ** 2
        played = np.abs(np.fft.rfft(estimate[: len(reference)], n=len(reference))) ** 2
        energies = {
            center: (float(np.sum(written[band])), float(np.sum(played[band])))
            for center in self._bands
            if np.any(band := (frequencies >= center / OCTAVE_HALF_WIDTH) & (frequencies < center * OCTAVE_HALF_WIDTH))
        }
        fullest = max((energy for energy, _ in energies.values()), default=0.0)
        floor = fullest * 10 ** (-self._band_floor_decibels / DECIBELS_PER_POWER_DECADE)
        return {
            f"{BAND_PREFIX}{center:g}": DECIBELS_PER_POWER_DECADE
            * math.log10((played_energy + LEVEL_FLOOR) / written_energy)
            for center, (written_energy, played_energy) in energies.items()
            if written_energy > floor and written_energy > 0.0
        }


def _spread(levels: np.ndarray) -> float:
    if not levels.size:
        return 0.0

    return float(np.percentile(levels, HIGH_PERCENTILE) - np.percentile(levels, LOW_PERCENTILE))
