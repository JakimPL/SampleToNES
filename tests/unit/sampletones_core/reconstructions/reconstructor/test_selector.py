from __future__ import annotations

import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


class TestTwoStageScoring:
    def test_shortlist_is_ranked_by_aligned_cost_best_first(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        remaining_generators = dict(worker.generators.items())
        remaining_generator_classes = worker.get_remaining_generator_classes(remaining_generators)
        scored = worker.selector._score_candidates(synthetic_fragment, remaining_generator_classes)

        assert 0 < len(scored) <= worker.selector.top_k
        costs = [candidate.cost for candidate in scored]
        assert costs == sorted(costs)

    def test_phase_shifted_target_selects_its_source_instruction_at_near_zero_cost(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        """
        A target that is a phase-shifted rendering of a library instruction wins with
        a near-zero cost: the spectral shortlist is phase-independent, and the
        temporal term is evaluated on the candidate aligned to the target, so the
        phase accident carries no penalty.
        """
        instruction = audible_instruction
        library_fragment = library_data[instruction]
        shifted_target = library_fragment.get_fragment(library_fragment.length // 4, config, window)

        remaining_generators = dict(worker.generators.items())
        remaining_generator_classes = worker.get_remaining_generator_classes(remaining_generators)
        scored = worker.selector._score_candidates(shifted_target, remaining_generator_classes)

        assert scored[0].instruction == instruction
        assert scored[0].cost == pytest.approx(0.0, abs=1e-3)
