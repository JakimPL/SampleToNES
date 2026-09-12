from dataclasses import replace
from typing import Dict, Final, List, Optional, Sequence, Tuple

from codec_study.measure import Measurement

STRATEGY_ORDER: Final[Tuple[str, ...]] = (
    "baseline",
    "seeds-trimmed",
    "seeds-both-4",
    "seeds-split-4",
    "search-long",
    "search-wide",
    "search-deep",
)
DEPTH_PREFIX: Final[str] = "depth-"


def depth_measurements(
    measurements: Sequence[Measurement],
    order: Sequence[str],
) -> Tuple[Measurement, ...]:
    """What an export trying the first ``d`` strategies and keeping the smallest would write.

    An export option choosing how deep to search is modeled as a list of encoder-side
    strategies tried in order: at each depth a song is written by whichever of the strategies so
    far made it smallest, and the time is what all of them took together. A strategy a song
    offers nothing to keeps the song where the previous depth left it.

    Args:
        measurements: Every song under every variant the run measured.
        order: The strategies, in the order an export would try them.

    Returns:
        Tuple[Measurement, ...]: One measurement per song and depth, named ``depth-d``, in song
            order then depth order.
    """
    present = [name for name in order if any(measurement.variant == name for measurement in measurements)]
    derived: List[Measurement] = []
    for name in dict.fromkeys(measurement.song.name for measurement in measurements):
        by_variant: Dict[str, Measurement] = {
            measurement.variant: measurement for measurement in measurements if measurement.song.name == name
        }
        derived.extend(_song_depths(by_variant, present))

    return tuple(derived)


def _song_depths(
    by_variant: Dict[str, Measurement],
    present: Sequence[str],
) -> List[Measurement]:
    depths: List[Measurement] = []
    best: Optional[Measurement] = None
    seconds = 0.0
    for depth, name in enumerate(present, start=1):
        measured = by_variant.get(name)
        if measured is not None:
            seconds += measured.seconds
            if best is None or measured.block < best.block:
                best = measured

        if best is not None:
            depths.append(
                Measurement(
                    song=best.song,
                    variant=f"{DEPTH_PREFIX}{depth}",
                    encoding=replace(best.encoding, seconds=seconds),
                )
            )

    return depths
