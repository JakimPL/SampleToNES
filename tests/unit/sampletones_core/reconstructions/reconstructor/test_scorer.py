from __future__ import annotations

from typing import Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import get_remaining_generator_classes
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.scorer import Scorer
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


def _candidate_approximations(
    worker: ReconstructorWorker,
) -> Tuple[Tuple[InstructionUnion, ...], Fragment]:
    remaining_generator_classes = get_remaining_generator_classes(dict(worker.channels))
    return worker.candidate_provider.candidates(remaining_generator_classes)


class TestSpectralCosts:
    def test_library_waveform_scores_its_source_instruction_at_zero(
        self,
        worker: ReconstructorWorker,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        instructions, candidates = _candidate_approximations(worker)
        costs = worker.scorer.spectral_costs(synthetic_fragment, candidates)
        source_index = instructions.index(audible_instruction)

        assert costs.shape == (len(instructions),)
        assert float(costs[source_index]) == pytest.approx(0.0, abs=1e-5)

    def test_costs_are_independent_of_the_target_phase(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        """
        Spectral costs compare phase-averaged features, so the same waveform rendered
        at two phases receives identical costs.
        """
        instruction = audible_instruction
        library_fragment = library_data[instruction]
        target = library_fragment.get_fragment(0, config, window)
        shifted_target = library_fragment.get_fragment(library_fragment.length // 4, config, window)

        _, candidates = _candidate_approximations(worker)
        costs = worker.scorer.spectral_costs(target, candidates)
        shifted_costs = worker.scorer.spectral_costs(shifted_target, candidates)
        np.testing.assert_allclose(shifted_costs, costs, rtol=1e-6)


class TestAlignedCost:
    def test_alignment_forgives_the_target_phase(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        """
        The aligned cost evaluates the temporal term at the candidate's best phase
        against the target, so a phase-shifted rendering of the candidate itself
        scores at zero while the unaligned rendering carries the phase accident.
        """
        instruction = audible_instruction
        library_fragment = library_data[instruction]
        shifted_target = library_fragment.get_fragment(library_fragment.length // 4, config, window)

        aligned = worker.phase_aligner.align(shifted_target, instruction)
        unaligned = library_fragment.get_fragment(0, config, window)

        aligned_cost = worker.scorer.aligned_cost(shifted_target, 0.0, aligned)
        unaligned_cost = worker.scorer.aligned_cost(shifted_target, 0.0, unaligned)

        assert aligned_cost == pytest.approx(0.0, abs=1e-4)
        assert aligned_cost < unaligned_cost

    def test_blends_spectral_and_temporal_terms_with_the_configured_weights(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        instruction = audible_instruction
        library_fragment = library_data[instruction]
        target = library_fragment.get_fragment(0, config, window)
        aligned = worker.phase_aligner.align(target, instruction)

        spectral_cost = 0.5
        cost = worker.scorer.aligned_cost(target, spectral_cost, aligned)
        assert cost == pytest.approx(worker.scorer.criterion.alpha * spectral_cost, abs=1e-5)


class TestTopK:
    def test_top_k_is_ascending(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        _, candidates = _candidate_approximations(worker)
        costs = worker.scorer.spectral_costs(synthetic_fragment, candidates)
        indices = Scorer.top_k(costs, 3)
        assert int(indices[0]) == int(np.argmin(costs))
        assert bool(np.all(np.diff(costs[indices]) >= 0.0))

    def test_top_k_clamps_to_candidate_count(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        _, candidates = _candidate_approximations(worker)
        costs = worker.scorer.spectral_costs(synthetic_fragment, candidates)
        indices = Scorer.top_k(costs, costs.shape[0] + 10)
        assert indices.shape[0] == costs.shape[0]
