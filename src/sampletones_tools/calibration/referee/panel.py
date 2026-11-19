from dataclasses import dataclass
from typing import Tuple

from .factory import build_conversion_referees, build_referees, build_truth_referees
from .protocol import ConversionReferee, Referee, TruthReferee


@dataclass(frozen=True)
class RefereePanel:
    """Every referee a run judges a conversion with.

    Attributes:
        audio: Referees comparing the render with its recording, the headline one first.
        truth: Referees reading the conversion against what its sound plays, where the corpus knows it.
        conversion: Referees reading the conversion on its own.
    """

    audio: Tuple[Referee, ...]
    truth: Tuple[TruthReferee, ...]
    conversion: Tuple[ConversionReferee, ...]


def build_panel(sample_rate: int) -> RefereePanel:
    """Every referee available on this system, with the packaged tuning."""
    return RefereePanel(
        audio=tuple(build_referees(sample_rate)),
        truth=tuple(build_truth_referees()),
        conversion=tuple(build_conversion_referees()),
    )
