from __future__ import annotations

import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import (
    get_generator_by_instruction,
    get_remaining_generator_classes,
)
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


class TestTwoStageScoring:
    def test_shortlist_is_ranked_by_aligned_cost_best_first(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        remaining_generator_classes = get_remaining_generator_classes(dict(worker.channels))
        scored = worker.matcher.score_candidates(synthetic_fragment, remaining_generator_classes)

        assert 0 < len(scored) <= worker.matcher.top_k
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

        remaining_generator_classes = get_remaining_generator_classes(dict(worker.channels))
        scored = worker.matcher.score_candidates(shifted_target, remaining_generator_classes)

        assert scored[0].instruction == instruction
        assert scored[0].cost == pytest.approx(0.0, abs=1e-3)


class TestClassRestrictedShortlist:
    def test_one_class_keeps_the_candidate_a_wider_scoring_picked(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        """Scoring one generator class alone reaches the winner the wider scoring picked.

        The shortlist is drawn by spectral rank, so a candidate that outranked every other
        class's candidates outranks its own class's rejects too. That is what lets a frame's
        ownership be settled across classes while the column the decoder reads holds the
        winning channel's own alternatives.
        """
        wide_classes = get_remaining_generator_classes(dict(worker.channels))
        winner = worker.matcher.score_candidates(synthetic_fragment, wide_classes)[0]
        generator = get_generator_by_instruction(winner.instruction, wide_classes)

        column = worker.matcher.score_candidates(
            synthetic_fragment,
            {generator.class_name(): generator},
        )

        assert winner.instruction in [candidate.instruction for candidate in column]
