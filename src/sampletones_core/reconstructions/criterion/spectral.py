from typing import Tuple

from sampletones_core.constants.algorithm import SPECTRUM_FLOOR
from sampletones_core.constants.enums import SpectralDistance
from sampletones_shared.array import xp

from .alignment import align_candidates


def calculate_spectral_loss(
    reference: xp.ndarray,
    candidates: xp.ndarray,
    weights: xp.ndarray,
    *,
    distance: SpectralDistance,
    divergence_beta: float,
) -> xp.ndarray:
    """
    Weighted spectral distance between a target feature and candidate features.

    The per-bin distances are weighted and normalized by the target's own weighted
    energy, so the score reflects spectral shape at every target level. The
    `SPECTRUM_FLOOR` in the denominator keeps the ratio finite for silent targets.

    Args:
        reference: Target feature values, one dimension.
        candidates: Candidate feature values, one candidate per row.
        weights: Per-bin weights of the configuration.
        distance: Per-bin distance family.
        divergence_beta: Beta parameter of the beta-divergence distance.

    Returns:
        One loss per candidate.

    Raises:
        ValueError: If the reference has more than one dimension.
        ValueError: If the candidate width departs from the reference length.
        ValueError: If the spectral distance is unsupported.
    """
    reference, candidates, weights = _prepare(reference, candidates, weights)

    match distance:
        case SpectralDistance.SQUARED:
            numerator = xp.sqrt(
                xp.sum(
                    weights * (candidates - reference) ** 2,
                    axis=-1,
                )
            )
            denominator = xp.sqrt(xp.sum(weights * reference**2, axis=-1))
        case SpectralDistance.ABSOLUTE:
            numerator = xp.sum(weights * xp.abs(candidates - reference), axis=-1)
            denominator = xp.sum(weights * reference, axis=-1)
        case SpectralDistance.BETA_DIVERGENCE:
            numerator = xp.sum(
                weights
                * _beta_divergence(
                    reference,
                    candidates,
                    divergence_beta,
                ),
                axis=-1,
            )
            denominator = xp.sum(weights * reference, axis=-1)
        case _:
            raise ValueError(f"Unsupported spectral distance: {distance}")

    return numerator / (denominator + SPECTRUM_FLOOR)


def _prepare(
    reference: xp.ndarray,
    candidates: xp.ndarray,
    weights: xp.ndarray,
) -> Tuple[xp.ndarray, xp.ndarray, xp.ndarray]:
    reference, candidates = align_candidates(reference, candidates)
    if weights.ndim == 1:
        weights = weights.reshape((1, -1))

    return reference, candidates, weights


def _beta_divergence(
    reference: xp.ndarray,
    candidates: xp.ndarray,
    beta: float,
) -> xp.ndarray:
    reference = reference + SPECTRUM_FLOOR
    candidates = candidates + SPECTRUM_FLOOR

    if beta == 1.0:
        return reference * (xp.log(reference) - xp.log(candidates)) + (candidates - reference)

    if beta == 0.0:
        ratio = reference / candidates
        return ratio - xp.log(ratio) - 1.0

    return (reference**beta + (beta - 1.0) * candidates**beta - beta * reference * candidates ** (beta - 1.0)) / (
        beta * (beta - 1.0)
    )
