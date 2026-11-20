import numpy as np

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_shared.array import CUPY_AVAILABLE, to_numpy, xp

from ..criterion import Criterion


class Scorer:
    """
    Scores what a frame sounds like against the target fragment, in two stages.

    `spectral_costs` ranks a stack of mixed features by the phase-independent spectral term,
    producing the shortlist. `frame_costs` completes the criterion for shortlisted mixes with the
    temporal term their expected waveforms measure, and charges each channel a mix sounds the
    configured price.
    """

    def __init__(self, config: Config, window: Window, signal_length: int) -> None:
        self.criterion = Criterion(config, window, signal_length)
        self.channel_price = config.generation.weights.channel_price

    def spectral_costs(self, target: Fragment, features: xp.ndarray) -> np.ndarray:
        """
        Weighted spectral loss of every mixed feature against the target.

        The mixed features sum powers averaged over phase, so the ranking is independent of how
        the candidate waveforms are phased.

        Args:
            target: Target fragment to match.
            features: Feature values of the mixes, one mix per row.

        Returns:
            One spectral cost per mix.
        """
        errors = None
        target_values = None
        try:
            target_values = xp.asarray(target.feature.values)
            errors = self.criterion.spectral_loss(target_values, features)
            return np.asarray(to_numpy(errors), dtype=np.float64)
        finally:
            del errors, target_values
            if CUPY_AVAILABLE:
                xp.get_default_memory_pool().free_all_blocks()

    def shortfall_weighted_costs(self, target: Fragment, features: xp.ndarray, shortfall_weight: float) -> np.ndarray:
        """
        The spectral cost of every mixed feature, with what each falls short of counted at ``shortfall_weight``.

        Args:
            target: Target fragment to match.
            features: Feature values of the mixes, one mix per row.
            shortfall_weight: The share of its usual cost a bin a mix falls short in counts.

        Returns:
            One cost per mix.
        """
        errors = None
        target_values = None
        try:
            target_values = xp.asarray(target.feature.values)
            errors = self.criterion.shortfall_weighted_loss(target_values, features, shortfall_weight)
            return np.asarray(to_numpy(errors), dtype=np.float64)
        finally:
            del errors, target_values
            if CUPY_AVAILABLE:
                xp.get_default_memory_pool().free_all_blocks()

    def frame_costs(
        self,
        target: Fragment,
        spectral_costs: np.ndarray,
        expectations: np.ndarray,
        variances: np.ndarray,
        sounding: np.ndarray,
    ) -> np.ndarray:
        """
        Full criterion cost of every mix, with the temporal term its expected waveform measures.

        The criterion is relative to the frame's own sound, so the price of a sounding channel is a
        share of that sound as well.

        Args:
            target: Target fragment to match.
            spectral_costs: The mixes' spectral costs from `spectral_costs`.
            expectations: The waveform each mix is expected to render, one mix per row.
            variances: The per-sample variance of each mix about its expected waveform.
            sounding: How many channels each mix sounds.

        Returns:
            One blended criterion cost per mix, the price of its sounding channels included.
        """
        temporal = self.criterion.expected_temporal_loss(
            xp.asarray(target.audio, dtype=xp.float64),
            xp.asarray(expectations),
            xp.asarray(variances),
        )
        combined = self.criterion.combine_losses(xp.asarray(spectral_costs), temporal)
        priced = np.asarray(to_numpy(combined), dtype=np.float64).reshape(-1)
        return priced + self.channel_price * np.asarray(sounding, dtype=np.float64).reshape(-1)

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
