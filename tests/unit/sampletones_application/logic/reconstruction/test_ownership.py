from typing import Dict, Final, List, Sequence, Tuple

from sampletones_application.logic.reconstruction.ownership import ownership_lanes
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

CHANNEL: Final[ChannelName] = ChannelName.PULSE1
STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
STEM_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]


def _stems_data(stem_ids: Sequence[int]) -> StemsData:
    """A record of two recordings, the first channel holding ``stem_ids`` frame by frame."""
    entries = [
        StemEntry(
            id=stem_id,
            settings=StemSettings(channels=STEM_CHANNELS, bends=bending_channels(STEM_CHANNELS)),
        )
        for stem_id in (STEM_A, STEM_B)
    ]
    return StemsData(
        config=StemsConfig(entries=entries, hierarchy=StemsHierarchy(levels=[[STEM_A, STEM_B]])),
        assignments=[ChannelAssignment(channel_name=CHANNEL, stem_ids=list(stem_ids))],
    )


def _lane_runs(stem_ids: Sequence[int]) -> Tuple[Tuple[int, int, int], ...]:
    """The stretches the first channel divides into, each as its start, end and owner."""
    assignments: Dict[ChannelName, List[int]] = {CHANNEL: list(stem_ids)}
    lanes = ownership_lanes(_stems_data(stem_ids), assignments, lambda _channel: {STEM_A, STEM_B})
    return tuple((run.start_frame, run.end_frame, run.stem_id) for run in lanes[CHANNEL].runs)


class TestWhatALaneDividesInto:
    """A lane names an owner wherever the record does, and a rest answers to none.

    A resting stretch shows the ground of whatever surface carries the lane, so a stretch painted
    for it would take the ribbon's own ground onto a plot answering to a different color.
    """

    def test_each_recording_takes_the_stretch_it_holds(self) -> None:
        assert _lane_runs([STEM_A, STEM_A, STEM_B]) == ((0, 2, STEM_A), (2, 3, STEM_B))

    def test_a_resting_stretch_takes_none_of_its_own(self) -> None:
        assert _lane_runs([STEM_A, RESTING_STEM_ID, STEM_B]) == ((0, 1, STEM_A), (2, 3, STEM_B))

    def test_a_channel_resting_throughout_carries_no_stretch(self) -> None:
        assert _lane_runs([RESTING_STEM_ID, RESTING_STEM_ID]) == ()

    def test_a_trailing_rest_leaves_the_recordings_where_they_stand(self) -> None:
        assert _lane_runs([STEM_A, STEM_A, RESTING_STEM_ID]) == ((0, 2, STEM_A),)
