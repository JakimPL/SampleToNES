from typing import Tuple

from sampletones_core.constants.enums import SpectralDistance
from sampletones_shared.array import xp

from .alignment import align_candidates
from .metric import SpectralMetric


def calculate_spectral_loss(
    reference: xp.ndarray,
    candidates: xp.ndarray,
    weights: xp.ndarray,
    *,
    metric: SpectralMetric,
) -> xp.ndarray:
    """
    Weighted spectral distance between a target feature and candidate features.

    The per-bin distances are weighted and divided by the target's own weighted energy, so a
    score reflects spectral shape at every target level. Every side measures power above the
    target's `spectral_floor`, which keeps the reading finite for silent targets.

    Args:
        reference: Target feature values, one dimension.
        candidates: Candidate feature values, one candidate per row.
        weights: Per-bin weights of the configuration.
        metric: The distance family and the scale bins are measured on.

    Returns:
        One loss per candidate.

    Raises:
        ValueError: If the reference has more than one dimension.
        ValueError: If the candidate width departs from the reference length.
        ValueError: If the spectral distance is unsupported.
    """
    reference, candidates, weights = _prepare(reference, candidates, weights)
    floor = spectral_floor(reference, metric=metric)

    match metric.distance:
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
                    metric.divergence_beta,
                    floor,
                ),
                axis=-1,
            )
        case _:
            raise ValueError(f"Unsupported spectral distance: {metric.distance}")

    denominator = weighted_reference_energy(reference, weights, distance=metric.distance)
    return numerator / (denominator + floor)


def spectral_floor(reference: xp.ndarray, *, metric: SpectralMetric) -> xp.ndarray:
    """
    The power a bin of the target's frame is measured above, set by that frame's loudest bin.

    The floor sits the metric's dynamic range under the loudest bin, so a candidate's addition is
    charged wherever it stays audible beside what the frame sounds, at every frame loudness: quiet
    noise under a loud tone costs what it adds, and noise filling a frame costs what it leaves out.
    A frame whose loudest bin lies under the metric's silence floor is measured from that level,
    which keeps the floor positive for a silent frame.

    Args:
        reference: Target feature values.
        metric: The scale the frame is measured on.

    Returns:
        The floor, as a scalar on the active array backend.
    """
    loudest = xp.maximum(xp.max(reference), metric.silence_floor)
    return loudest * 10.0 ** (-metric.dynamic_range_decibels / 10.0)


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
    floor: xp.ndarray,
) -> xp.ndarray:
    """
    Per-bin beta-divergence of the floored candidates from the floored reference.

    Every branch reads the divergence off the relative difference `u` of the two spectra, in double
    precision, and returns it in the reference's precision. The divergence of a small `u` is about
    `u² / 2` while its rounding stays near machine epsilon times `|u|`, so double precision measures
    a candidate whose spectrum differs from the reference by a millionth as finely as a loud one.
    """
    precision = reference.dtype
    reference = reference.astype(xp.float64)
    candidates = candidates.astype(xp.float64)
    floor = xp.asarray(floor, dtype=xp.float64)
    floored_reference = reference + floor
    floored_candidates = candidates + floor

    if beta == 1.0:
        divergence = floored_reference * _log_excess((candidates - reference) / floored_reference)
    elif beta == 0.0:
        divergence = _log_excess((reference - candidates) / floored_candidates)
    else:
        relative = (reference - candidates) / floored_candidates
        excess = xp.expm1(beta * xp.log1p(relative)) - beta * relative
        divergence = floored_candidates**beta * excess / (beta * (beta - 1.0))

    return divergence.astype(precision)


def _log_excess(relative: xp.ndarray) -> xp.ndarray:
    """`u - log(1 + u)`, the divergence of a ratio `1 + u` from one, which vanishes quadratically at `u = 0`."""
    return relative - xp.log1p(relative)
