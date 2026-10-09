from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def two_stems() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=0,
                settings=StemSettings(channels=[ChannelName.PULSE1, ChannelName.PULSE2], bends=[ChannelName.PULSE1]),
            ),
            StemEntry(
                id=1,
                settings=StemSettings(channels=[ChannelName.NOISE], bends=[]),
            ),
        ],
        hierarchy=StemsHierarchy(levels=[[0, 1]]),
    )
