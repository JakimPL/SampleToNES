import numpy as np

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_shared.array import CUPY_AVAILABLE, to_numpy, xp

from ..criterion import Criterion
from .approximation import Approximation


class Scorer:
    """
    Scores candidate approximations against a target fragment in two stages.

    `spectral_costs` ranks the whole candidate stack by the phase-independent
    spectral term, producing the shortlist. `candidate_cost` completes the criterion
    for one shortlisted candidate with the temporal term its approximation measures.
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

    def reference_energy(self, target: Fragment) -> float:
        """
        How much sound a target holds, in the units its spectral loss is measured in.

        A spectral cost is a fraction of this quantity, so multiplying the two states a covering
        in absolute terms, which is what lets two targets of different loudness be compared.

        Args:
            target: Target fragment to measure.

        Returns:
            The target's weighted energy.
        """
        energy = self.criterion.reference_energy(xp.asarray(target.feature.values))
        return float(to_numpy(energy).reshape(-1)[0])

    def silence_cost(self, target: Fragment) -> float:
        """
        Full criterion cost of leaving a target silent, the cost every candidate improves on.

        Silence is scored as a candidate whose feature and waveform are zero, through the same
        spectral and temporal terms and the same blend, so a candidate's cost reads against it on
        one scale.

        Args:
            target: Target fragment to measure.

        Returns:
            The blended criterion cost of silence.
        """
        feature = xp.asarray(target.feature.values)
        audio = xp.asarray(target.audio)
        spectral = self.criterion.spectral_loss(feature, xp.zeros_like(feature)[None, :])
        temporal = self.criterion.temporal_loss(audio, xp.zeros_like(audio)[None, :])
        combined = self.criterion.combine_losses(spectral, temporal)
        return float(to_numpy(combined).reshape(-1)[0])

    def candidate_cost(
        self,
        target: Fragment,
        spectral_cost: float,
        approximation: Approximation,
    ) -> float:
        """
        Full criterion cost of one candidate, with the temporal term the candidate's
        approximation measures against the target.

        Combines the already-computed spectral cost with that temporal loss, using the
        configured loss blend.

        Args:
            target: Target fragment to match.
            spectral_cost: The candidate's spectral cost from `spectral_costs`.
            approximation: The candidate as the matching built it for this target.

        Returns:
            The blended criterion cost.
        """
        temporal = approximation.temporal_loss(target, self.criterion)
        combined = self.criterion.combine_losses(spectral_cost, temporal)
        return float(to_numpy(combined)[0])

    @staticmethod
    def top_k(costs: np.ndarray, k: int) -> np.ndarray:
        """The indices of the ``k`` lowest costs, ordered best first.

        Args:
            costs: One cost per candidate.
            k: How many candidates to keep; clamped to the number available.

        Returns:
            np.ndarray: The selected indices, sorted by ascending cost.
        """
        count = min(k, int(costs.shape[0]))
        partitioned = np.argpartition(costs, count - 1)[:count]
        return partitioned[np.argsort(costs[partitioned])]
