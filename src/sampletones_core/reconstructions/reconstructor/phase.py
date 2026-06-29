from abc import ABC, abstractmethod
from typing import Dict, Type

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import fftconvolve

from sampletones_core.configs import Config
from sampletones_core.constants.enums import PhaseAlignerName
from sampletones_core.fft import Fragment, Window
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
    def align(self, fragment: Fragment, instruction: InstructionUnion) -> Fragment: ...


class SlidingRmsePhaseAligner(PhaseAligner):
    def align(self, fragment: Fragment, instruction: InstructionUnion) -> Fragment:
        library_fragment = self.library_data[instruction]
        array = library_fragment.sample.get_fragment(length=2 * library_fragment.sample.length)

        windows = sliding_window_view(array, self.config.library.frame_length)
        remainder = fragment.audio - windows

        rmse = np.sqrt((remainder**2).mean(axis=1))
        best_shift = int(np.argmin(rmse))
        return library_fragment.get_fragment(best_shift, self.config, self.window)


class CrossCorrelationPhaseAligner(PhaseAligner):
    def align(self, fragment: Fragment, instruction: InstructionUnion) -> Fragment:
        library_fragment = self.library_data[instruction]
        frame_length = self.config.library.frame_length
        array = library_fragment.sample.get_fragment(length=2 * library_fragment.sample.length)
        target = np.asarray(fragment.audio, dtype=np.float64)

        correlation = fftconvolve(array.astype(np.float64), target[::-1], mode="valid")
        window_energy = self._sliding_energy(array, frame_length)
        cost = window_energy - 2.0 * correlation
        best_shift = int(np.argmin(cost))
        return library_fragment.get_fragment(best_shift, self.config, self.window)

    @staticmethod
    def _sliding_energy(array: np.ndarray, frame_length: int) -> np.ndarray:
        squared = np.asarray(array, dtype=np.float64) ** 2
        cumulative = np.concatenate([np.zeros(1, dtype=np.float64), np.cumsum(squared)])
        energy: np.ndarray = np.asarray(cumulative[frame_length:] - cumulative[:-frame_length])
        return energy


PHASE_ALIGNERS: Dict[PhaseAlignerName, Type[PhaseAligner]] = {
    PhaseAlignerName.SLIDING_RMSE: SlidingRmsePhaseAligner,
    PhaseAlignerName.CROSS_CORRELATION: CrossCorrelationPhaseAligner,
}
