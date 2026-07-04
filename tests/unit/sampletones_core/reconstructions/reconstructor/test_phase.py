from __future__ import annotations

from typing import Type

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.phase import (
    CrossCorrelationPhaseAligner,
    PhaseAligner,
    SlidingRmsePhaseAligner,
)


def _rmse(target: Fragment, aligned: Fragment) -> float:
    difference = np.asarray(target.audio) - np.asarray(aligned.audio)
    return float(np.sqrt(np.mean(difference**2)))


class TestPhaseAlignerEquivalence:
    def test_cross_correlation_reaches_the_sliding_rmse_optimum(
        self,
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
    ) -> None:
        sliding = SlidingRmsePhaseAligner(config, window, library_data)
        cross_correlation = CrossCorrelationPhaseAligner(config, window, library_data)

        active_instructions = [instruction for instruction in library_data.keys() if instruction.on]
        assert active_instructions

        for instruction in active_instructions:
            target = library_data[instruction].get_fragment(0, config, window)
            sliding_rmse = _rmse(target, sliding.align(target, instruction))
            cross_correlation_rmse = _rmse(target, cross_correlation.align(target, instruction))

            assert cross_correlation_rmse == pytest.approx(sliding_rmse, abs=1e-6)
            assert cross_correlation_rmse == pytest.approx(0.0, abs=1e-4)


class TestPhaseAlignerDrive:
    @pytest.mark.parametrize("aligner_class", [SlidingRmsePhaseAligner, CrossCorrelationPhaseAligner])
    def test_aligned_candidate_matches_a_drive_scaled_target(
        self,
        aligner_class: Type[PhaseAligner],
        config: Config,
        window: Window,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
    ) -> None:
        """
        The aligner searches and returns the candidate at the amplitude it competes
        at, so a target that is a drive-scaled, phase-shifted rendering of the
        candidate is reproduced exactly.
        """
        drive = 2.0
        driven_config = config.model_copy(update={"generation": config.generation.model_copy(update={"drive": drive})})
        aligner = aligner_class(driven_config, window, library_data)

        library_fragment = library_data[audible_instruction]
        target = library_fragment.get_fragment(library_fragment.length // 4, config, window) * drive
        aligned = aligner.align(target, audible_instruction)

        assert _rmse(target, aligned) == pytest.approx(0.0, abs=1e-4)
