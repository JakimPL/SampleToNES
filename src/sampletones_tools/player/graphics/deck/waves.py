from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Tuple

from sampletones_tools.player.graphics.deck.groups import (
    CHROME_GROUP,
    OTHER_WAVE_GROUP,
    PULSE_WAVE_GROUP,
    TileName,
)

WAVE_PERIODS: Final[int] = 2
BLANK: Final[TileName] = TileName(CHROME_GROUP, "blank")


@dataclass(frozen=True)
class Wave:
    """One period of a channel's wave shape: two tiles above two tiles."""

    top: Tuple[TileName, TileName]
    bottom: Tuple[TileName, TileName]

    @classmethod
    def of(cls, group: str, top: Tuple[str, str], bottom: Tuple[str, str]) -> Wave:
        """The shape whose tiles one group holds, an empty tile standing wherever the wave leaves one.

        Args:
            group: The tile group the drawn members belong to.
            top: The members of the upper row, left to right.
            bottom: The members of the lower row, left to right.

        Returns:
            Wave: The period, each member named with its group.
        """
        return cls(
            top=(cls._named(group, top[0]), cls._named(group, top[1])),
            bottom=(cls._named(group, bottom[0]), cls._named(group, bottom[1])),
        )

    @staticmethod
    def _named(group: str, member: str) -> TileName:
        return BLANK if member == BLANK.member else TileName(group, member)


PULSE_WAVES: Final[Tuple[Wave, ...]] = (
    Wave.of(PULSE_WAVE_GROUP, ("spike_top", "blank"), ("spike_bottom", "floor")),
    Wave.of(PULSE_WAVE_GROUP, ("quarter_top", "blank"), ("quarter_bottom", "floor")),
    Wave.of(PULSE_WAVE_GROUP, ("crest_top", "half_top"), ("stem_bottom", "half_bottom")),
    Wave.of(PULSE_WAVE_GROUP, ("crest_top", "late_top"), ("stem_bottom", "late_bottom")),
)
PULSE_REST: Final[Wave] = Wave.of(PULSE_WAVE_GROUP, ("rest_top", "rest_top"), ("rest_bottom", "rest_bottom"))
OTHER_REST: Final[Wave] = Wave.of(OTHER_WAVE_GROUP, ("rest_top", "rest_top"), ("rest_bottom", "rest_bottom"))
TRIANGLE_WAVE: Final[Wave] = Wave.of(OTHER_WAVE_GROUP, ("rise_top", "fall_top"), ("rise_bottom", "fall_bottom"))
NOISE_WAVES: Final[Dict[bool, Tuple[Wave, Wave]]] = {
    False: (
        Wave.of(OTHER_WAVE_GROUP, ("hiss_a", "hiss_b"), ("hiss_b", "hiss_a")),
        Wave.of(OTHER_WAVE_GROUP, ("hiss_b", "hiss_a"), ("hiss_a", "hiss_b")),
    ),
    True: (
        Wave.of(OTHER_WAVE_GROUP, ("buzz_a", "buzz_b"), ("buzz_b", "buzz_a")),
        Wave.of(OTHER_WAVE_GROUP, ("buzz_b", "buzz_a"), ("buzz_a", "buzz_b")),
    ),
}
