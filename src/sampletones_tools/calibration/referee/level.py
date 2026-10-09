import numpy as np

from sampletones_core.fft.fft import k_weighting


def k_weighted_energy(audio: np.ndarray, sample_rate: int) -> float:
    """The energy of a signal as loudness weighs it: its power spectrum summed under the K-weighting curve."""
    spectrum = np.fft.rfft(audio.astype(np.float64))
    frequencies = np.fft.rfftfreq(audio.shape[0], 1.0 / sample_rate)
    return float(np.sum(k_weighting(frequencies) * np.abs(spectrum) ** 2))


def level_difference_decibels(
    reference: np.ndarray,
    estimate: np.ndarray,
    sample_rate: int,
    *,
    energy_floor: float,
    range_decibels: float,
) -> float:
    """
    How much louder the estimate plays than the reference, in decibels of K-weighted energy.

    The energy floor keeps a silent signal's level finite, and the reading is held within
    ``range_decibels`` either way, so a silent estimate reads as the whole range quieter.

    Args:
        reference: Reference waveform.
        estimate: Waveform under evaluation.
        sample_rate: Sampling rate of both signals in Hz.
        energy_floor: Energy added to both sides before the ratio.
        range_decibels: The largest difference reported, in either direction.

    Returns:
        float: The level difference, positive when the estimate is louder.
    """
    reference_energy = k_weighted_energy(reference, sample_rate) + energy_floor
    estimate_energy = k_weighted_energy(estimate, sample_rate) + energy_floor
    difference = 10.0 * np.log10(estimate_energy / reference_energy)
    return float(np.clip(difference, -range_decibels, range_decibels))


def matched_to_reference(estimate: np.ndarray, *, level_decibels: float) -> np.ndarray:
    """The estimate brought to the reference's level, given how much louder it plays."""
    matched: np.ndarray = estimate * 10.0 ** (-level_decibels / 20.0)
    return matched
