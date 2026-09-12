from dataclasses import dataclass
from typing import Final

from codec_study.sandbox.costs import PRODUCTION_COSTS, Costs


@dataclass(frozen=True)
class Grammar:
    """One token grammar the sandbox prices a plane under.

    The baseline grammar is the codec as it stands, and every other one switches a change on
    over it, so what a change earns is read as the difference between the two on the same plane
    and the same dictionary.

    Attributes:
        every_length: Whether a hold of every length is offered beside the longest one (H9a).
        start_hold: Whether a hold may open a stream, over the value the driver seeds every
            plane to (H9b).
        wide_hold: Whether a wide hold covers blocks of a plain hold's longest reach at once (H1).
        set_hold: Whether one token sets a value and holds it (H3).
        default_counts: Whether a phrase carries a default count a token may leave unstated (H4).
        costs: The bytes each token takes.
    """

    every_length: bool
    start_hold: bool
    wide_hold: bool
    set_hold: bool
    default_counts: bool
    costs: Costs


BASELINE_GRAMMAR: Final[Grammar] = Grammar(
    every_length=False,
    start_hold=False,
    wide_hold=False,
    set_hold=False,
    default_counts=False,
    costs=PRODUCTION_COSTS,
)
