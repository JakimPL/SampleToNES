from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_shared.array import xp


def driven_powers(powers: xp.ndarray, drive: float) -> xp.ndarray:
    """Library powers as a channel played at ``drive`` reads them.

    A drive ``d`` asks a channel to play its part of the stem's audio ``d`` times louder. The stem's
    audio is one target for all its channels, each at its own drive, so the rows are scaled instead:
    each is read at ``1 / d`` of its library amplitude, its power divided by ``d²``, and the row
    matching the audio is the one ``d`` times louder. At unit drive the powers stand as they are.

    Args:
        powers: Power densities per bin as the library sample plays them, on either array backend.
        drive: The level the stem gives the channel.

    Returns:
        The powers at the drive, on the backend ``powers`` came on.
    """
    if drive == UNIT_DRIVE:
        return powers

    return powers / drive**2
