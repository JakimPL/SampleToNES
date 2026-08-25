from dataclasses import dataclass
from typing import Final, Optional

import numpy as np

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY

from .cqt.frequencies import calculate_cqt_frequencies
from .cqt.transform import calculate_cqt_frames

HARMONIC_COUNT: Final[int] = 5
MINIMUM_COLUMN_ENERGY: Final[float] = 1e-20


@dataclass(frozen=True)
class FundamentalReading:
    """What a frame's partials place its fundamental at, and how much of the frame stands behind it.

    Attributes:
        frequency: The fundamental in Hz the frame's harmonics agree on.
        confidence: The share of the frame's energy those harmonics hold, in ``[0, 1]``.
    """

    frequency: float
    confidence: float


class InstantaneousPitch:
    """Where a recording's partials actually sit, read frame by frame from the transform's phase.

    A constant-Q column carries a phase as well as a magnitude, and a partial standing between two
    bin centers still advances that phase at its own rate. Comparing the phase two columns apart
    against the rate the bin itself would turn at therefore states the partial's frequency far more
    finely than the bins are spaced — finely enough to place a note within a fraction of a cent,
    where the bins alone place it within a semitone.

    Reading around a stated reference is what makes the answer usable: the reference names which
    bins carry the note's harmonics, and each harmonic's estimate is divided back down and weighted
    by the energy standing behind it. The harmonics are read in order, each one settled against the
    fundamental the ones below it agreed on, which is what keeps an upper harmonic on the right side
    of the whole turn its phase states the reading to within.
    """

    def __init__(
        self,
        audio: np.ndarray,
        sample_rate: int,
        hop_length: int,
        *,
        cutoff: float = CQT_CUTOFF_FREQUENCY,
        bins_per_octave: int = BINS_PER_OCTAVE,
    ) -> None:
        coefficients = calculate_cqt_frames(audio, sample_rate, hop_length, cutoff, None, bins_per_octave)
        self._magnitudes: np.ndarray = np.abs(coefficients)
        self._phases: np.ndarray = np.angle(coefficients)
        self._frequencies: np.ndarray = calculate_cqt_frequencies(
            coefficients.shape[0],
            cutoff,
            bins_per_octave,
        )
        self._energies: np.ndarray = np.sum(self._magnitudes**2, axis=0)
        self._turn_per_column: np.ndarray = 2.0 * np.pi * self._frequencies * hop_length / sample_rate
        self._resolution: float = sample_rate / (2.0 * np.pi * hop_length)
        self._ambiguity: float = sample_rate / hop_length

    @property
    def columns(self) -> int:
        """How many frames the transform read."""
        return int(self._magnitudes.shape[1])

    def at(self, frame: int, reference: float) -> Optional[FundamentalReading]:
        """Where the fundamental sits in one frame, read around a reference it is known to be near.

        Args:
            frame: The frame to read.
            reference: The frequency in Hz the note is expected at.

        Returns:
            Optional[FundamentalReading]: The reading, or ``None`` where the frame lies outside
                the transform or the reference names no bin the transform covers.
        """
        opening, closing = self._pair(frame)
        if opening is None or closing is None:
            return None

        weighted = 0.0
        weight = 0.0
        running = reference
        for harmonic in range(1, HARMONIC_COUNT + 1):
            bin_index = self._bin_for(reference * harmonic)
            if bin_index is None:
                continue

            partial = self._partial_frequency(bin_index, opening, closing, running * harmonic)
            energy = float(self._magnitudes[bin_index, opening]) ** 2
            weighted += energy * partial / harmonic
            weight += energy
            running = weighted / weight

        if weight <= 0.0:
            return None

        return FundamentalReading(
            frequency=weighted / weight,
            confidence=weight / max(float(self._energies[opening]), MINIMUM_COLUMN_ENERGY),
        )

    def _pair(self, frame: int) -> tuple[Optional[int], Optional[int]]:
        """The two columns a phase advance is read across, stepping back at the final frame."""
        if frame < 0 or frame >= self.columns:
            return None, None

        if frame + 1 < self.columns:
            return frame, frame + 1

        if frame > 0:
            return frame - 1, frame

        return None, None

    def _bin_for(self, frequency: float) -> Optional[int]:
        """The bin whose center stands nearest a frequency, where the transform reaches it."""
        if frequency < self._frequencies[0] or frequency > self._frequencies[-1]:
            return None

        return int(np.argmin(np.abs(self._frequencies - frequency)))

    def _partial_frequency(
        self,
        bin_index: int,
        opening: int,
        closing: int,
        expected: float,
    ) -> float:
        """What the partial in one bin sounds at, from how far its phase turned between two columns.

        A phase states its turn to within a whole turn, so the reading repeats every
        ``sample_rate / hop`` hertz and the branch to take is the one standing nearest where the
        partial is expected. That spacing is far wider than any error the reading itself carries,
        so choosing by the expectation settles the branch without moving the answer inside it —
        which is what keeps the upper harmonics of a note usable, since a whole turn there spans
        less than the semitone their bin covers.

        Args:
            bin_index: The bin the partial stands in.
            opening: The column the turn is measured from.
            closing: The column the turn is measured to.
            expected: The frequency in Hz the partial is expected near.

        Returns:
            float: The partial's frequency in Hz.
        """
        turned = self._phases[bin_index, closing] - self._phases[bin_index, opening]
        deviation = np.angle(np.exp(1j * (turned - self._turn_per_column[bin_index])))
        partial = float(self._frequencies[bin_index] + deviation * self._resolution)
        return partial + self._ambiguity * round((expected - partial) / self._ambiguity)
