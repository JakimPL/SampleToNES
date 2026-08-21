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
                hierarchy=StemsHierarchy(levels=[[0]]),
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


class TestStemsConfigHierarchy:
    """The hierarchy is the order the entries pick in, so it names each of them once."""

    def test_a_duplicated_stem_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            StemsConfig(
                entries=[StemEntry(id=0, channels=[ChannelName.PULSE1])],
                hierarchy=StemsHierarchy(levels=[[0], [0]]),
            )

    def test_a_stem_left_out_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            StemsConfig(
                entries=[
                    StemEntry(id=0, channels=[ChannelName.PULSE1]),
                    StemEntry(id=1, channels=[ChannelName.NOISE]),
                ],
                hierarchy=StemsHierarchy(levels=[[0]]),
            )

    def test_an_unknown_stem_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            StemsConfig(
                entries=[StemEntry(id=0, channels=[ChannelName.PULSE1])],
                hierarchy=StemsHierarchy(levels=[[0], [5]]),
            )


class TestStemsConfigViews:
    def test_entries_are_keyed_by_their_id(self) -> None:
        stems = _stems_config()
        assert set(stems.entries_by_id) == {0, 1}
        assert stems.entries_by_id[1].channels == [ChannelName.NOISE]

    def test_covered_channels_gather_every_entry(self) -> None:
        stems = _stems_config()
        assert stems.covered_channels == frozenset({ChannelName.PULSE1, ChannelName.NOISE})

    def test_frame_budget_stops_at_the_covered_channels(self) -> None:
        stems = _stems_config()
        assert stems.frame_budget == len(stems.covered_channels)

    def test_frame_budget_stops_at_the_cap(self) -> None:
        stems = StemsConfig(
            entries=[StemEntry(id=0, channels=[ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE])],
            hierarchy=StemsHierarchy(levels=[[0]]),
            channel_cap=1,
        )
        assert stems.frame_budget == 1


class TestSingleEntry:
    def test_names_one_stem_over_every_channel(self) -> None:
        channels = [ChannelName.PULSE1, ChannelName.TRIANGLE]
        stems = StemsConfig.single_entry(channels)

        assert [entry.channels for entry in stems.entries] == [channels]
        assert stems.hierarchy.levels == [[0]]
        assert stems.covered_channels == frozenset(channels)

    def test_carries_the_cap_it_is_given(self) -> None:
        stems = StemsConfig.single_entry([ChannelName.PULSE1, ChannelName.TRIANGLE], channel_cap=1)
        assert stems.channel_cap == 1
        assert stems.frame_budget == 1
