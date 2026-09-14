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
        case SpectralDistance.ABSOLUTE:
            numerator = xp.sum(weights * xp.abs(candidates - reference), axis=-1)
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
        case _:
            raise ValueError(f"Unsupported spectral distance: {distance}")

    denominator = weighted_reference_energy(reference, weights, distance=distance)
    return numerator / (denominator + SPECTRUM_FLOOR)


def weighted_reference_energy(
    reference: xp.ndarray,
    weights: xp.ndarray,
    *,
    distance: SpectralDistance,
) -> xp.ndarray:
    """
    The target's own weighted energy, the scale its spectral distance is measured against.

    Every distance family divides by this quantity, so a loss reads as a fraction of what the
    target holds. Read on its own it says how much there is to cover, which is what separates a
    loud target from a quiet one when two targets are compared.

    Args:
        reference: Target feature values.
        weights: Per-bin weights of the configuration.
        distance: Per-bin distance family the energy is measured for.

    Returns:
        The weighted energy, in the units the matching distance produces.

    Raises:
        ValueError: If the spectral distance is unsupported.
    """
    match distance:
        case SpectralDistance.SQUARED:
            return xp.sqrt(xp.sum(weights * reference**2, axis=-1))
        case SpectralDistance.ABSOLUTE | SpectralDistance.BETA_DIVERGENCE:
            return xp.sum(weights * reference, axis=-1)
        case _:
            raise ValueError(f"Unsupported spectral distance: {distance}")


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
    """
    Per-bin beta-divergence of the floored candidates from the floored reference.

    Every branch reads the divergence off the relative difference of the two spectra, so its
    rounding follows the size of the divergence, and a spectrum lying at the floor is measured as
    finely as a loud one. The general branch divides by `beta - 1`, which magnifies its rounding
    as `beta` nears one, and computes in double precision.
    """
    floored_reference = reference + SPECTRUM_FLOOR
    floored_candidates = candidates + SPECTRUM_FLOOR

    if beta == 1.0:
        return floored_reference * _log_excess((candidates - reference) / floored_reference)

    if beta == 0.0:
        return _log_excess((reference - candidates) / floored_candidates)

    floored_candidates = floored_candidates.astype(xp.float64)
    relative = (reference.astype(xp.float64) - candidates) / floored_candidates
    excess = xp.expm1(beta * xp.log1p(relative)) - beta * relative
    divergence = floored_candidates**beta * excess / (beta * (beta - 1.0))
    return divergence.astype(reference.dtype)


def _log_excess(relative: xp.ndarray) -> xp.ndarray:
    """`u - log(1 + u)`, the divergence of a ratio `1 + u` from one, which vanishes quadratically at `u = 0`."""
    return relative - xp.log1p(relative)
