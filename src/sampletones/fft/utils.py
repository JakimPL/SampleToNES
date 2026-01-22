import numpy as np


def rectangle_window(length: int) -> np.ndarray:
    """
    Create a rectangular (uniform) window.

    Args:
        length: Window length.

    Returns:
        Array of ones with the specified length.
    """
    return np.ones(length, dtype=float)


def to_log_even_bands(
    bands: np.ndarray,
    cutoff: float,
    log_even_components: int,
) -> np.ndarray:
    """
    Generate logarithmically-spaced frequency band edges.

    Creates evenly-spaced bins on a logarithmic scale from cutoff frequency
    to the maximum frequency in the input bands.

    Args:
        bands: Original frequency band edges.
        cutoff: Cutoff frequency.
        log_even_components: Number of logarithmically spaced components.

    Returns:
        Array of log-spaced frequency edges.
    """
    size: int = log_even_components or len(bands)
    return np.exp(np.linspace(np.log(cutoff), np.log(bands[-1]), size + 1))
