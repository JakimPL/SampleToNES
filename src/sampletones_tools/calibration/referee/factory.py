from typing import List

from sampletones_tools.calibration.config.referee import RefereeConfig

from .auditory import MultiResolutionAuditoryReferee
from .loudness import LoudnessWeightedReferee
from .pitch import PitchReferee
from .protocol import Referee, TruthReferee
from .stability import StabilityReferee
from .transcription import TranscriptionReferee
from .zimtohrli import ZimtohrliReferee, zimtohrli_available


def build_referees(sample_rate: int) -> List[Referee]:
    """
    Referees available on this system, the headline one first.

    A report ranks by the first referee. The built-in referees share the packaged tuning, and
    Zimtohrli joins as a second opinion where the ``calibration`` dependency group is installed.

    Args:
        sample_rate: Sampling rate of the signals under evaluation in Hz.

    Returns:
        List[Referee]: The built-in referees with the packaged tuning, then Zimtohrli when available.
    """
    config = RefereeConfig.load()
    referees: List[Referee] = [
        MultiResolutionAuditoryReferee(sample_rate, config=config),
        LoudnessWeightedReferee(sample_rate, config=config),
    ]
    if zimtohrli_available():
        referees.append(ZimtohrliReferee(sample_rate))

    return referees


def build_truth_referees() -> List[TruthReferee]:
    """Referees reading a conversion against what its reference sound plays, with the packaged tuning.

    Returns:
        List[TruthReferee]: The transcription, the pitch and the stability referees.
    """
    config = RefereeConfig.load()
    return [
        TranscriptionReferee(volume_tolerance=config.volume_tolerance),
        PitchReferee(),
        StabilityReferee(),
    ]
