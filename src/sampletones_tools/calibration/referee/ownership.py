from typing import Dict, Final, Optional, Sequence

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.reconstructions import Reconstruction

from .protocol import Judgment

OWNERSHIP_REFEREE: Final[str] = "ownership"
SINGLE_STEM: Final[int] = 1


class OwnershipReferee:
    """Reads how often the channels of a stems conversion pass from one stem to another.

    A channel changes owner where the stem holding it gives way to another, a rest in between
    counting for nothing, so a stem picking its channel back up after a pause keeps it. The score is
    the owner changes per second over every channel, and each channel's own reading follows it.
    """

    @property
    def name(self) -> str:
        return OWNERSHIP_REFEREE

    def judge(self, reconstruction: Reconstruction) -> Optional[Judgment]:
        """The owner changes per second of ``reconstruction``'s channels.

        Returns:
            Optional[Judgment]: The judgment, or ``None`` for a conversion of one stem.
        """
        stems_data = reconstruction.stems_data
        if len(stems_data.config.entries) <= SINGLE_STEM:
            return None

        assignments = stems_data.assignments_by_channel
        frames = max((len(owners) for owners in assignments.values()), default=0)
        if not frames:
            return None

        seconds = frames / reconstruction.config.library.nes_frequency
        components: Dict[str, float] = {
            channel.value: owner_changes(owners) / seconds for channel, owners in assignments.items()
        }
        return Judgment(score=sum(components.values()), components=components)


def owner_changes(owners: Sequence[int]) -> int:
    """How many times the frames pass from one stem to another, rests set aside."""
    held = [owner for owner in owners if owner != RESTING_STEM_ID]
    return sum(previous != current for previous, current in zip(held, held[1:]))
