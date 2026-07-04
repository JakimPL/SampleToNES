import numpy as np

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_shared.array import CUPY_AVAILABLE, to_numpy, xp

from ..criterion import Criterion


class Scorer:
    """
    Scores candidate approximations against a target fragment in two stages.

    `spectral_costs` ranks the whole candidate stack by the phase-independent
    spectral term, producing the shortlist. `aligned_cost` completes the criterion
    for one shortlisted candidate, evaluating the temporal term on the candidate's
    phase-aligned waveform so it measures shape rather than the accident of phase.
    """

    def __init__(self, config: Config, window: Window, signal_length: int) -> None:
        self.criterion = Criterion(config, window, signal_length)

    def spectral_costs(self, target: Fragment, candidates: Fragment) -> np.ndarray:
        """
        Weighted spectral loss of every candidate against the target.

        Both sides are compared through their spectral features, which are averaged
        over phase for library candidates, so the ranking is independent of how the
        candidate waveforms are phased.

        Args:
            target: Target fragment to match.
            candidates: Stacked candidate fragments.

        Returns:
            One spectral cost per candidate.
        """
        errors = None
        target_gpu = None
        try:
            target_gpu = target.to_cupy()
            errors = self.criterion.spectral_loss(
                target_gpu.feature,
                candidates.feature,
            )
            return to_numpy(errors)
        finally:
            del errors, target_gpu
            if CUPY_AVAILABLE:
                xp.get_default_memory_pool().free_all_blocks()

    def aligned_cost(
        self,
        target: Fragment,
        spectral_cost: float,
        approximation: Fragment,
    ) -> float:
        """
        Full criterion cost of one candidate, with the temporal term evaluated on the
        candidate's aligned waveform.

        Combines the already-computed spectral cost with the temporal loss between the
        target and the aligned approximation, using the configured loss blend.

        Args:
            target: Target fragment to match.
            spectral_cost: The candidate's spectral cost from `spectral_costs`.
            approximation: The candidate fragment built at its best phase.

        Returns:
            The blended criterion cost.
        """
        temporal = self.criterion.temporal_loss(
            xp.asarray(target.audio),
            xp.asarray(approximation.audio),
        )
        combined = self.criterion.combine_losses(spectral_cost, temporal)
        return float(to_numpy(combined)[0])

    @staticmethod
    def top_k(costs: np.ndarray, k: int) -> np.ndarray:
        count = min(k, int(costs.shape[0]))
        partitioned = np.argpartition(costs, count - 1)[:count]
        return partitioned[np.argsort(costs[partitioned])]
