from typing import Union

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
    expectation: Union[float, xp.ndarray],
    variance: Union[float, xp.ndarray],
    *,
    level_floor: float,
) -> xp.ndarray:
    """
    RMS difference expected between a waveform and candidates known up to a spread about a waveform.

    A candidate's expectation is the waveform it is expected to render: its rendering at a known
    phase, or the mean level of a candidate standing at every phase alike. Its variance is its
    spread about that expectation, so the expected squared difference is the squared difference
    from the expectation plus the variance. The root of that expectation normalizes by the target's
    level as `calculate_temporal_loss` does, so the two losses stand on one scale.

    Args:
        audio: Target waveform, one dimension.
        expectation: The expected waveforms, one candidate per row, or one waveform or level every
            candidate shares.
        variance: The per-sample variance of each candidate, or one variance every candidate shares.
        level_floor: Lowest target level the loss normalizes by.

    Returns:
        One loss per candidate.

    Raises:
        ValueError: If the target has more than one dimension.
    """
    reference = xp.asarray(audio)
    if reference.ndim != 1:
        raise ValueError("audio must be 1D")

    expected = xp.asarray(expectation)
    if expected.ndim < 2:
        expected = xp.reshape(expected, (1, -1))

    mean_square = xp.mean(xp.square(reference[None, :] - expected), axis=-1) + xp.reshape(xp.asarray(variance), (-1,))
    level = xp.sqrt(xp.mean(xp.square(reference)))
    return xp.sqrt(mean_square) / xp.maximum(level, level_floor)
