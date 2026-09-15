from abc import ABC, abstractmethod
from typing import Dict, Type

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import fftconvolve

from sampletones_core.configs import Config
from sampletones_core.constants.enums import PhaseAlignerName
from sampletones_core.fft import Window
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData


class PhaseAligner(ABC):
    def __init__(
        self,
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
    ) -> None:
        self.config = config
        self.window = window
        self.library_data = library_data

    @abstractmethod
    def align(self, waveform: np.ndarray, instruction: InstructionUnion) -> np.ndarray:
        """The frame the candidate renders at its best phase against ``waveform``, at the configured drive."""

    def _rendering(self, instruction: InstructionUnion, shift: int) -> np.ndarray:
        """The candidate's frame starting ``shift`` samples into its library sample, at the configured drive."""
        fragment = self.library_data[instruction].get_fragment(shift, self.config, self.window)
        return np.asarray(fragment.audio, dtype=np.float64) * self.config.generation.drive

    def _cycle(self, instruction: InstructionUnion) -> np.ndarray:
        """Two cycles of the candidate's library sample, which every shift of one frame reads from."""
        sample = self.library_data[instruction].sample
        return np.asarray(sample.get_fragment(length=2 * sample.length), dtype=np.float64)


class SlidingRmsePhaseAligner(PhaseAligner):
    """
    Finds the cyclic shift minimizing the RMSE between the waveform and the drive-scaled
    candidate, and returns the candidate's frame at that shift.
    """

    def align(self, waveform: np.ndarray, instruction: InstructionUnion) -> np.ndarray:
        drive = self.config.generation.drive
        windows = sliding_window_view(self._cycle(instruction), self.config.library.frame_length)
        remainder = np.asarray(waveform, dtype=np.float64) - drive * windows

        rmse = np.sqrt((remainder**2).mean(axis=1))
        return self._rendering(instruction, int(np.argmin(rmse)))


class CrossCorrelationPhaseAligner(PhaseAligner):
    """
    Finds the cyclic shift minimizing the squared error between the waveform and the
    drive-scaled candidate via FFT cross-correlation, expanding
    `||waveform - drive * candidate||^2` into a per-shift cost of
    `drive * energy - 2 * correlation` (the constant waveform energy and the positive
    drive factor drop out of the argmin), and returns the candidate's frame at that shift.
    The sliding energy of a candidate depends on its library sample alone, so it is read once
    per instruction.
    """

    def __init__(
        self,
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
    ) -> None:
        super().__init__(config, window, library_data)
        self._energies: Dict[InstructionUnion, np.ndarray] = {}

    def align(self, waveform: np.ndarray, instruction: InstructionUnion) -> np.ndarray:
        drive = self.config.generation.drive
        cycle = self._cycle(instruction)
        target = np.asarray(waveform, dtype=np.float64)

        correlation = fftconvolve(cycle, target[::-1], mode="valid")
        cost = drive * self._sliding_energy(instruction, cycle) - 2.0 * correlation
        return self._rendering(instruction, int(np.argmin(cost)))

    def _sliding_energy(self, instruction: InstructionUnion, cycle: np.ndarray) -> np.ndarray:
        energy = self._energies.get(instruction)
        if energy is None:
            frame_length = self.config.library.frame_length
            cumulative = np.concatenate([np.zeros(1, dtype=np.float64), np.cumsum(cycle**2)])
            energy = np.asarray(cumulative[frame_length:] - cumulative[:-frame_length])
            self._energies[instruction] = energy

        return energy


PHASE_ALIGNERS: Dict[PhaseAlignerName, Type[PhaseAligner]] = {
    PhaseAlignerName.SLIDING_RMSE: SlidingRmsePhaseAligner,
    PhaseAlignerName.CROSS_CORRELATION: CrossCorrelationPhaseAligner,
}
