import pytest
from pydantic import ValidationError

from sampletones_core.constants.algorithm import DEFAULT_STEMS_CHANNEL_CAP
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


def _stems_config() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(id=0, channels=[ChannelName.PULSE1]),
            StemEntry(id=1, channels=[ChannelName.NOISE]),
        ],
        hierarchy=StemsHierarchy(levels=[[0], [1]], mode=HierarchyMode.STRICT),
        channel_cap=DEFAULT_STEMS_CHANNEL_CAP,
    )


class TestStemsConfig:
    def test_defaults_to_an_empty_assignment(self) -> None:
        stems = StemsConfig()
        assert stems.entries == []
        assert stems.hierarchy.levels == []
        assert stems.hierarchy.mode == HierarchyMode.ROUND_ROBIN
        assert stems.channel_cap == DEFAULT_STEMS_CHANNEL_CAP

    def test_duplicate_entry_ids_raise(self) -> None:
        with pytest.raises(ValidationError):
            StemsConfig(
                entries=[
                    StemEntry(id=0, channels=[ChannelName.PULSE1]),
                    StemEntry(id=0, channels=[ChannelName.NOISE]),
                ],
            )

    def test_channel_cap_below_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            StemsConfig(channel_cap=0)

    def test_fields(self) -> None:
        stems = _stems_config()
        assert [entry.id for entry in stems.entries] == [0, 1]
        assert stems.hierarchy.levels == [[0], [1]]
        assert stems.hierarchy.mode == HierarchyMode.STRICT
        assert stems.channel_cap == DEFAULT_STEMS_CHANNEL_CAP
