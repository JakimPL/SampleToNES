from typing import Dict, Final, List

import pytest

from sampletones_core.constants.enums import AssignmentMethod, ChannelName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.assigners import PicksAssigner, frame_assigner
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.assigner import JointAssigner
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite

LATTICE_WIDTH: Final[int] = 8
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()


class TestFrameAssigner(BaseTestSuite):
    @pytest.mark.parametrize(
        "method, kind",
        [(AssignmentMethod.PICKS, PicksAssigner), (AssignmentMethod.JOINT, JointAssigner)],
        ids=["picks", "joint"],
    )
    def test_the_method_names_the_assigner(
        self,
        method: AssignmentMethod,
        kind: type,
        all_channels: Dict[ChannelName, GeneratorUnion],
        joint_matcher: FrameMatcher,
    ) -> None:
        stems = StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL))

        assert isinstance(frame_assigner(method, stems, all_channels, joint_matcher, LATTICE_WIDTH), kind)
