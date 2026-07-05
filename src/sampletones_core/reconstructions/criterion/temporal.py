from sampletones_shared.array import xp


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
    reference = xp.asarray(audio)
    candidates = xp.asarray(approximation)

    if reference.ndim != 1:
        raise ValueError("reference must be 1D")

    if candidates.ndim == 1:
        candidates = candidates[None, :]
    elif candidates.shape[1] != reference.shape[0]:
        raise ValueError(f"candidate width {candidates.shape[1]} does not match reference length {reference.shape[0]}")

    rmse = xp.sqrt(xp.mean(xp.square(candidates - reference), axis=-1))
    level = xp.sqrt(xp.mean(xp.square(reference)))
    return rmse / xp.maximum(level, level_floor)
