from typing import Tuple

from sampletones_shared.array import xp


def align_candidates(
    reference: xp.ndarray,
    candidates: xp.ndarray,
) -> Tuple[xp.ndarray, xp.ndarray]:
    """Brings a target and its candidates to the shape every loss reads them in.

    A loss scores one target against a stack of candidates, so the target becomes a single row and
    each candidate a row beside it. A lone candidate is read as a stack of one, which lets a caller
    score a single approximation through the same path as a whole batch.

    Args:
        reference: Target values, one dimension.
        candidates: Candidate values, one candidate per row, or a lone candidate.

    Returns:
        The target as one row, paired with the candidates as a stack of rows.

    Raises:
        ValueError: If the reference has more than one dimension.
        ValueError: If the candidate width departs from the reference length.
    """
    reference = xp.asarray(reference)
    candidates = xp.asarray(candidates)

    if reference.ndim != 1:
        raise ValueError("reference must be 1D")

    if candidates.ndim == 1:
        candidates = candidates[None, :]
    elif candidates.shape[1] != reference.shape[0]:
        raise ValueError(f"candidate width {candidates.shape[1]} does not match reference length {reference.shape[0]}")

    return reference.reshape((1, -1)), candidates
