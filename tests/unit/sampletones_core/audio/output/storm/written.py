from bisect import bisect_left
from dataclasses import dataclass
from typing import Dict, List, Self, Sequence, Set

import numpy as np

from tests.suite.audio.timeline import TimelineEvent, Written

from .source import identity_of, level_of


@dataclass(frozen=True)
class WrittenSounds:
    """Which sound every block the device took carried, read back from the levels its samples state.

    Attributes:
        blocks: The timeline index of every block each sound carried, by sound.
        carried: The sounds each stream carried, by stream.
        strays: Each block carrying more than one sound, or a level no sound plays.
    """

    blocks: Dict[int, List[int]]
    carried: Dict[int, Set[int]]
    strays: List[str]

    @classmethod
    def read(cls, events: Sequence[TimelineEvent]) -> Self:
        blocks: Dict[int, List[int]] = {}
        carried: Dict[int, Set[int]] = {}
        strays: List[str] = []
        for index, event in enumerate(events):
            if not isinstance(event, Written):
                continue

            levels = [float(level) for level in np.unique(event.samples[event.samples != 0])]
            identities = sorted({identity_of(level) for level in levels})
            if len(identities) > 1:
                strays.append(f"stream {event.stream} wrote a block carrying sounds {identities}")

            if any(level_of(identity_of(level)) != level for level in levels):
                strays.append(f"stream {event.stream} wrote a level no sound plays")

            for identity in identities:
                blocks.setdefault(identity, []).append(index)
                carried.setdefault(event.stream, set()).add(identity)

        return cls(blocks=blocks, carried=carried, strays=strays)

    def before(self, identity: int, index: int) -> int:
        """How many blocks of the sound the device took before the timeline held ``index`` events."""
        return bisect_left(self.blocks.get(identity, []), index)

    def after(self, identity: int, index: int) -> int:
        """How many blocks of the sound the device took once the timeline held ``index`` events."""
        return len(self.blocks.get(identity, [])) - self.before(identity, index)
