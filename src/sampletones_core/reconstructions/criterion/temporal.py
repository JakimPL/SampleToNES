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


def calculate_expected_temporal_loss(
    audio: xp.ndarray,
    expectation: float,
    variance: float,
    *,
    level_floor: float,
) -> xp.ndarray:
    """
    RMS difference expected between a waveform and a candidate taken at a phase chosen at random.

    A candidate standing at every phase alike contributes its mean at each sample and its spread
    about that mean, so the expected squared difference is the squared difference from the mean
    plus the variance. The root of that expectation normalizes by the target's level as
    `calculate_temporal_loss` does, so the two losses stand on one scale.

    Args:
        audio: Target waveform, one dimension.
        expectation: The candidate's mean level.
        variance: The candidate's variance about its mean.
        level_floor: Lowest target level the loss normalizes by.

    Returns:
        The loss, as a stack of one.

    Raises:
        ValueError: If the target has more than one dimension.
    """
    reference = xp.asarray(audio)
    if reference.ndim != 1:
        raise ValueError("audio must be 1D")

    mean_square = xp.mean(xp.square(reference - expectation)) + variance
    level = xp.sqrt(xp.mean(xp.square(reference)))
    return xp.reshape(xp.sqrt(mean_square) / xp.maximum(level, level_floor), (1,))
