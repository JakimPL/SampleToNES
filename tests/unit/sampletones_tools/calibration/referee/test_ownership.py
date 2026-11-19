from typing import Final

import pytest

from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.referee.ownership import OwnershipReferee, owner_changes

from .truths import converted, judged

FRAMES: Final[int] = 6
SECONDS: Final[float] = FRAMES / 60


class TestOwnerChanges:
    def test_a_rest_between_one_owner_s_stretches_counts_for_nothing(self) -> None:
        assert owner_changes([0, 0, RESTING_STEM_ID, 0, 1, 1]) == 1


class TestOwnershipReferee:
    def test_a_conversion_of_one_stem_is_left_unjudged(self) -> None:
        reconstruction = converted(
            {ChannelName.PULSE1: [PulseInstruction(on=True, pitch=69, volume=9, duty_cycle=2)] * FRAMES}
        )

        assert OwnershipReferee().judge(reconstruction) is None

    def test_a_channel_passing_between_stems_counts_its_owner_changes_per_second(self) -> None:
        reconstruction = converted(
            {ChannelName.PULSE1: [PulseInstruction(on=True, pitch=69, volume=9, duty_cycle=2)] * FRAMES}
        )
        stems = StemsConfig(
            entries=tuple(
                StemEntry(id=index, settings=StemSettings.covering([ChannelName.PULSE1])) for index in (0, 1)
            ),
            hierarchy=StemsHierarchy(levels=((0, 1),)),
        )
        record = StemsData(
            config=stems,
            assignments=(ChannelAssignment(channel_name=ChannelName.PULSE1, stem_ids=(0, 1, 0, 1, 1, 1)),),
            scale=1.0,
        )

        judgment = judged(OwnershipReferee().judge(reconstruction.model_copy(update={"stems_data": record})))

        assert judgment.components[ChannelName.PULSE1.value] == pytest.approx(3 / SECONDS)
