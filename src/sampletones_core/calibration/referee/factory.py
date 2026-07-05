from typing import List

from sampletones_core.calibration.config.referee import RefereeConfig

from .auditory import MultiResolutionAuditoryReferee
from .protocol import Referee
from .zimtohrli import ZimtohrliReferee, find_zimtohrli


def build_referees(sample_rate: int) -> List[Referee]:
    """
    Referees available on this system, the built-in one first.

    Args:
        sample_rate: Sampling rate of the signals under evaluation in Hz.

    Returns:
        The built-in multi-resolution referee with the packaged tuning, joined by
        the external psychoacoustic referee when its binary is installed.
    """
    referees: List[Referee] = [
        MultiResolutionAuditoryReferee(
            sample_rate,
            config=RefereeConfig.load(),
        ),
    ]
    binary = find_zimtohrli()
    if binary:
        referees.append(ZimtohrliReferee(sample_rate, binary))

    return referees
