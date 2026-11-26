import numpy as np

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_shared.array import xp


def driven_powers(powers: xp.ndarray, drive: float) -> xp.ndarray:
    """Library powers as a channel played at ``drive`` reads them.

    A drive ``d`` asks a channel to play its part of the stem's audio ``d`` times louder. The stem's
    audio is one target for all its channels, each at its own drive, so the rows are scaled instead:
    each is read at ``1 / d`` of its library amplitude (``driven_amplitudes``), its power divided by
    ``d²``, and the row matching the audio is the one ``d`` times louder. At unit drive the powers
    stand as they are.

    Args:
        powers: Power densities per bin as the library sample plays them, on either array backend.
        drive: The level the stem gives the channel.

    Returns:
        The powers at the drive, on the backend ``powers`` came on.
    """
    if drive == UNIT_DRIVE:
        return powers

    return powers / drive**2


def driven_amplitudes(amplitudes: np.ndarray, drive: float) -> np.ndarray:
    """Library amplitudes, a waveform or its mean level, as a channel played at ``drive`` reads them.

    A row is read at ``1 / d`` of its library amplitude, the half of the drive's rule that waveforms
    follow, as its power follows ``driven_powers``. At unit drive the amplitudes stand as they are.
    """
    if drive == UNIT_DRIVE:
        return amplitudes

    return amplitudes / drive


def driven_variance(variance: float, drive: float) -> float:
    """A library waveform's variance as a channel played at ``drive`` reads it, divided by ``d²`` as its power is."""
    if drive == UNIT_DRIVE:
        return variance

    return variance / drive**2
