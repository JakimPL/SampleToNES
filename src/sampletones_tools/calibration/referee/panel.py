from dataclasses import dataclass
from typing import Tuple

from sampletones_tools.calibration.config.referee import RefereeConfig

from .factory import build_conversion_referees, build_referees, build_trace_referees, build_truth_referees
from .protocol import ConversionReferee, Referee, TraceReferee, TruthReferee


@dataclass(frozen=True)
class RefereePanel:
    """Every referee a run judges a conversion with, and the tuning they were built with.

    A record's readings depend on which referees judged it and on their tuning, so the panel keeps
    both for the run's fingerprint to hold.

    Attributes:
        audio: Referees comparing the render with its recording, the headline one first.
        truth: Referees reading the conversion against what its sound plays, where the corpus knows it.
        trace: Referees reading the conversion's search against what its sound plays.
        conversion: Referees reading the conversion on its own.
        config: The tuning the referees were built with.
    """

    audio: Tuple[Referee, ...]
    truth: Tuple[TruthReferee, ...]
    trace: Tuple[TraceReferee, ...]
    conversion: Tuple[ConversionReferee, ...]
    config: RefereeConfig

    @property
    def names(self) -> Tuple[str, ...]:
        """Every referee's name, in the order a conversion is judged: audio, truth, trace, then conversion."""
        return (
            *(referee.name for referee in self.audio),
            *(referee.name for referee in self.truth),
            *(referee.name for referee in self.trace),
            *(referee.name for referee in self.conversion),
        )


def build_panel(sample_rate: int) -> RefereePanel:
    """Every referee available on this system, built with the packaged tuning read once."""
    config = RefereeConfig.load()
    return RefereePanel(
        audio=tuple(build_referees(sample_rate, config)),
        truth=tuple(build_truth_referees(config)),
        trace=tuple(build_trace_referees()),
        conversion=tuple(build_conversion_referees()),
        config=config,
    )
