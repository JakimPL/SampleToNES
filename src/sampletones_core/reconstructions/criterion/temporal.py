from sampletones_shared.array import xp

from .alignment import align_candidates


def calculate_temporal_loss(
    audio: xp.ndarray,
    approximation: xp.ndarray,
    *,
    level_floor: float,
) -> xp.ndarray:
    """
    RMS difference between waveforms, normalized by the target's own level.

    The normalization makes the temporal term relative, matching the spectral term,
    so the configured loss blend holds at every frame loudness. Frames quieter than
    `level_floor` normalize as if at that floor, keeping costs bounded for
    near-silent frames.

    Args:
        audio: Target waveform, one dimension.
        approximation: Candidate waveforms, one candidate per row.
        level_floor: Lowest target level the loss normalizes by.

    Returns:
        One loss per candidate.

    Raises:
        ValueError: If the target has more than one dimension.
        ValueError: If the candidate width departs from the target length.
    """
    reference, candidates = align_candidates(audio, approximation)

    rmse = xp.sqrt(xp.mean(xp.square(candidates - reference), axis=-1))
    level = xp.sqrt(xp.mean(xp.square(reference)))
    return rmse / xp.maximum(level, level_floor)
