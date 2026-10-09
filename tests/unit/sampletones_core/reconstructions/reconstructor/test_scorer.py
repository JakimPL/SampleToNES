from __future__ import annotations

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.candidates import ClassCandidates
from sampletones_core.reconstructions.reconstructor.scorer import Scorer
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


def _candidates(worker: ReconstructorWorker) -> ClassCandidates:
    """Every candidate of every kind the run hands out, stacked as one column would read them."""
    return worker.candidate_provider.candidates(
        {generator.class_name(): generator for generator in worker.channels.values()}
    )


class TestSpectralCosts:
    def test_library_feature_scores_its_source_instruction_at_zero(
        self,
        worker: ReconstructorWorker,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        candidates = _candidates(worker)
        costs = worker.scorer.spectral_costs(
            synthetic_fragment, worker.candidate_provider.features_of(candidates.powers)
        )
        source_index = candidates.instructions.index(audible_instruction)

        assert costs.shape == (len(candidates.instructions),)
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
        library_fragment = library_data[audible_instruction]
        target = library_fragment.get_fragment(0, config, window)
        shifted_target = library_fragment.get_fragment(library_fragment.length // 4, config, window)
        features = worker.candidate_provider.features_of(_candidates(worker).powers)

        costs = worker.scorer.spectral_costs(target, features)
        shifted_costs = worker.scorer.spectral_costs(shifted_target, features)
        np.testing.assert_allclose(shifted_costs, costs, rtol=1e-6)


class TestFrameCosts:
    def test_the_target_s_own_waveform_costs_nothing_over_time(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        audio = np.asarray(synthetic_fragment.audio, dtype=np.float64)

        costs = worker.scorer.frame_costs(synthetic_fragment, np.zeros(1), audio[None, :], np.zeros(1))

        assert float(costs[0]) == pytest.approx(0.0, abs=1e-6)

    def test_blends_spectral_and_temporal_terms_with_the_configured_weights(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        audio = np.asarray(synthetic_fragment.audio, dtype=np.float64)
        spectral_cost = 0.5

        cost = worker.scorer.frame_costs(synthetic_fragment, np.array([spectral_cost]), audio[None, :], np.zeros(1))

        assert float(cost[0]) == pytest.approx(worker.scorer.criterion.alpha * spectral_cost, abs=1e-5)

    def test_a_spread_costs_what_its_variance_adds(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        """A mix known up to a spread costs more over time than the same mix rendered exactly."""
        audio = np.asarray(synthetic_fragment.audio, dtype=np.float64)
        expectations = np.stack([audio, audio])

        exact, spread = worker.scorer.frame_costs(synthetic_fragment, np.zeros(2), expectations, np.array([0.0, 1e-3]))

        assert exact < spread


class TestTopK:
    def test_top_k_is_ascending(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        features = worker.candidate_provider.features_of(_candidates(worker).powers)
        costs = worker.scorer.spectral_costs(synthetic_fragment, features)
        indices = Scorer.top_k(costs, 3)
        assert int(indices[0]) == int(np.argmin(costs))
        assert bool(np.all(np.diff(costs[indices]) >= 0.0))

    def test_top_k_clamps_to_candidate_count(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        features = worker.candidate_provider.features_of(_candidates(worker).powers)
        costs = worker.scorer.spectral_costs(synthetic_fragment, features)
        indices = Scorer.top_k(costs, costs.shape[0] + 10)
        assert indices.shape[0] == costs.shape[0]
