from __future__ import annotations

from typing import Tuple

import numpy as np

from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.scorer import Scorer
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


def _candidate_approximations(worker: ReconstructorWorker) -> Tuple[object, Fragment]:
    remaining_generators = worker.get_remaining_generators()
    remaining_generator_classes = worker.get_remaining_generator_classes(remaining_generators)
    return worker.candidate_provider.candidates(remaining_generator_classes)


class TestScorerAgreement:
    def test_best_matches_argmin_of_costs(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        _, candidates = _candidate_approximations(worker)
        costs = worker.scorer.costs(synthetic_fragment, candidates)
        best = worker.scorer.best(synthetic_fragment, candidates)
        assert best == int(np.argmin(costs))

    def test_top_k_starts_with_best_and_is_ascending(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        _, candidates = _candidate_approximations(worker)
        costs = worker.scorer.costs(synthetic_fragment, candidates)
        best = worker.scorer.best(synthetic_fragment, candidates)
        indices = Scorer.top_k(costs, 3)
        assert int(indices[0]) == best
        assert bool(np.all(np.diff(costs[indices]) >= 0.0))

    def test_top_k_clamps_to_candidate_count(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        _, candidates = _candidate_approximations(worker)
        costs = worker.scorer.costs(synthetic_fragment, candidates)
        indices = Scorer.top_k(costs, costs.shape[0] + 10)
        assert indices.shape[0] == costs.shape[0]
