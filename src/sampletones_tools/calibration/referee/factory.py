from typing import List

from sampletones_tools.calibration.config.referee import RefereeConfig

from .auditory import MultiResolutionAuditoryReferee
from .balance import BalanceReferee
from .continuity import ContinuityReferee
from .contour import ContourReferee
from .loudness import LoudnessWeightedReferee
from .ownership import OwnershipReferee
from .pitch import PitchReferee
from .protocol import ConversionReferee, Referee, TraceReferee, TruthReferee
from .search import SearchReferee
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
        List[Referee]: The built-in referees with the packaged tuning (auditory, loudness, contour),
            then Zimtohrli when available.
    """
    config = RefereeConfig.load()
    referees: List[Referee] = [
        MultiResolutionAuditoryReferee(sample_rate, config=config),
        LoudnessWeightedReferee(sample_rate, config=config),
        ContourReferee(sample_rate, config=config),
    ]
    if zimtohrli_available():
        referees.append(ZimtohrliReferee(sample_rate))

    return referees


def build_truth_referees() -> List[TruthReferee]:
    """Referees reading a conversion against what its reference sound plays, with the packaged tuning.

    Returns:
        List[TruthReferee]: The transcription, the pitch, the stability, the balance and the continuity
            referees.
    """
    config = RefereeConfig.load()
    return [
        TranscriptionReferee(volume_tolerance=config.volume_tolerance, misplaced_weight=config.misplaced_weight),
        PitchReferee(),
        StabilityReferee(),
        BalanceReferee(),
        ContinuityReferee(),
    ]


def build_trace_referees() -> List[TraceReferee]:
    """Referees reading a conversion's search against what its reference sound plays.

    Returns:
        List[TraceReferee]: The search referee.
    """
    return [SearchReferee()]


def build_conversion_referees() -> List[ConversionReferee]:
    """Referees reading a conversion on its own.

    Returns:
        List[ConversionReferee]: The ownership referee.
    """
    return [OwnershipReferee()]
