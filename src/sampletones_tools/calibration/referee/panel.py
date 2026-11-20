from dataclasses import dataclass
from typing import Tuple

from .factory import build_conversion_referees, build_referees, build_trace_referees, build_truth_referees
from .protocol import ConversionReferee, Referee, TraceReferee, TruthReferee


@dataclass(frozen=True)
class RefereePanel:
    """Every referee a run judges a conversion with.

    Attributes:
        audio: Referees comparing the render with its recording, the headline one first.
        truth: Referees reading the conversion against what its sound plays, where the corpus knows it.
        trace: Referees reading the conversion's search against what its sound plays.
        conversion: Referees reading the conversion on its own.
    """

    audio: Tuple[Referee, ...]
    truth: Tuple[TruthReferee, ...]
    trace: Tuple[TraceReferee, ...]
    conversion: Tuple[ConversionReferee, ...]


def build_panel(sample_rate: int) -> RefereePanel:
    """Every referee available on this system, with the packaged tuning."""
    return RefereePanel(
        audio=tuple(build_referees(sample_rate)),
        truth=tuple(build_truth_referees()),
        trace=tuple(build_trace_referees()),
        conversion=tuple(build_conversion_referees()),
    )
