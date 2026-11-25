import math
from itertools import groupby
from typing import Dict, Final, List, Tuple

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
NO_SPREAD: Final[float] = 0.0
NO_ONSET: Final[float] = 0.0

BandEnergies = Tuple[float, float]
FrameRun = Tuple[int, int]


class ContourReferee:
    """Reads whether a render follows its recording's loudness over time and over the bands of the spectrum.

    Both signals are cut into frames of ``contour_frame_rate`` per second, each measured as its level in
    decibels: its mean power with ``LEVEL_FLOOR`` added, so a silent frame reads a finite level. A frame
    is audible where the recording plays it within ``contour_audible_decibels`` of its loudest frame.

    The score is the standard deviation, in decibels, of the render's level less the recording's over
    the audible frames: zero for a render that rises and falls exactly as the recording does, at any
    constant offset, so it reads the contour apart from the level. Its readings, each in decibels and
    closest at zero:

    - ``spread``: the range of the render's audible levels less the recording's, each read from the
      ``LOW_PERCENTILE``-th to the ``HIGH_PERCENTILE``-th percentile, so a render whose dynamics flatten
      reads below zero;
    - ``onset``: how much louder the render plays than the recording over the first frames of each
      audible run, up to ``contour_onset_frames`` of them, averaged over the runs, so a render that
      overshoots its attacks reads above zero;
    - ``band-F``: the render's energy less the recording's in the octave band centered on ``F`` hertz,
      over the bands the recording fills within ``contour_band_floor_decibels`` of its fullest band, so
      an implied equalization reads as a curve across the bands.
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
        """Each whole frame's level in decibels, the frame's mean power with the floor added."""
        frames = len(audio) // self._frame_length
        cut = np.asarray(audio[: frames * self._frame_length], dtype=np.float64).reshape(frames, self._frame_length)
        levels = DECIBELS_PER_POWER_DECADE * np.log10(np.mean(np.square(cut), axis=1) + LEVEL_FLOOR)
        return np.asarray(levels, dtype=np.float64)

    def _onset(self, written: np.ndarray, played: np.ndarray, audible: np.ndarray) -> float:
        """The render's level less the recording's over the first frames of each audible run, averaged over the runs."""
        runs = _audible_runs(audible)
        if not runs:
            return NO_ONSET

        rises: List[float] = []
        for start, end in runs:
            span = slice(start, min(start + self._onset_frames, end))
            rises.append(float(np.mean(played[span] - written[span])))

        return float(np.mean(rises))

    def _band_balance(self, reference: np.ndarray, estimate: np.ndarray) -> Dict[str, float]:
        """The render's energy less the recording's in decibels, for each octave band the recording fills."""
        energies = self._band_energies(reference, estimate)
        fullest = max((energy for energy, _ in energies.values()), default=0.0)
        floor = fullest * 10 ** (-self._band_floor_decibels / DECIBELS_PER_POWER_DECADE)
        return {
            f"{BAND_PREFIX}{center:g}": DECIBELS_PER_POWER_DECADE
            * math.log10((played_energy + LEVEL_FLOOR) / written_energy)
            for center, (written_energy, played_energy) in energies.items()
            if written_energy > floor and written_energy > 0.0
        }

    def _band_energies(self, reference: np.ndarray, estimate: np.ndarray) -> Dict[float, BandEnergies]:
        """The recording's and the render's spectral energy in each octave band holding a bin of the spectrum."""
        frequencies = np.fft.rfftfreq(len(reference), d=1.0 / self._sample_rate)
        written = np.abs(np.fft.rfft(reference)) ** 2
        played = np.abs(np.fft.rfft(estimate[: len(reference)], n=len(reference))) ** 2
        energies: Dict[float, BandEnergies] = {}
        for center in self._bands:
            band = _octave_band(frequencies, center)
            if np.any(band):
                energies[center] = (float(np.sum(written[band])), float(np.sum(played[band])))

        return energies


def _octave_band(frequencies: np.ndarray, center: float) -> np.ndarray:
    """Which ``frequencies`` lie in the octave centered on ``center``, half an octave to either side of it."""
    return np.asarray((frequencies >= center / OCTAVE_HALF_WIDTH) & (frequencies < center * OCTAVE_HALF_WIDTH))


def _audible_runs(audible: np.ndarray) -> List[FrameRun]:
    """Each run of audible frames, as its first frame and the frame after its last."""
    runs: List[FrameRun] = []
    start = 0
    for is_audible, frames in groupby(audible.tolist()):
        end = start + len(list(frames))
        if is_audible:
            runs.append((start, end))

        start = end

    return runs


def _spread(levels: np.ndarray) -> float:
    """The range of ``levels`` between the low and the high percentile, zero for no level."""
    if not levels.size:
        return NO_SPREAD

    return float(np.percentile(levels, HIGH_PERCENTILE) - np.percentile(levels, LOW_PERCENTILE))
