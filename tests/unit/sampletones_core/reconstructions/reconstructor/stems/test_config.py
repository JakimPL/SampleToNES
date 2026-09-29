import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def _stems_config() -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=0, settings=StemSettings(channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1]))
            ),
            StemEntry(
                id=1, settings=StemSettings(channels=[ChannelName.NOISE], bends=bending_channels([ChannelName.NOISE]))
            ),
        ],
        hierarchy=StemsHierarchy(levels=[[0], [1]], mode=HierarchyMode.STRICT),
    )


class TestStemsConfig:
    def test_defaults_to_an_empty_assignment(self) -> None:
        stems = StemsConfig()
        assert stems.entries == []
        assert stems.hierarchy.levels == []
        assert stems.hierarchy.mode == HierarchyMode.ROUND_ROBIN

    def test_duplicate_entry_ids_raise(self) -> None:
        with pytest.raises(ValidationError):
            StemsConfig(
                entries=[
                    StemEntry(
                        id=0,
                        settings=StemSettings(
                            channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])
                        ),
                    ),
                    StemEntry(
                        id=0,
                        settings=StemSettings(
                            channels=[ChannelName.NOISE], bends=bending_channels([ChannelName.NOISE])
                        ),
                    ),
                ],
                hierarchy=StemsHierarchy(levels=[[0]]),
            )

    def test_fields(self) -> None:
        stems = _stems_config()
        assert [entry.id for entry in stems.entries] == [0, 1]
        assert stems.hierarchy.levels == [[0], [1]]
        assert stems.hierarchy.mode == HierarchyMode.STRICT


class TestStemsConfigHierarchy:
    """The hierarchy is the order the entries pick in, so it names each of them once."""

    def test_a_duplicated_stem_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            StemsConfig(
                entries=[
                    StemEntry(
                        id=0,
                        settings=StemSettings(
                            channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])
                        ),
                    )
                ],
                hierarchy=StemsHierarchy(levels=[[0], [0]]),
            )

    def test_a_stem_left_out_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            StemsConfig(
                entries=[
                    StemEntry(
                        id=0,
                        settings=StemSettings(
                            channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])
                        ),
                    ),
                    StemEntry(
                        id=1,
                        settings=StemSettings(
                            channels=[ChannelName.NOISE], bends=bending_channels([ChannelName.NOISE])
                        ),
                    ),
                ],
                hierarchy=StemsHierarchy(levels=[[0]]),
            )

    def test_an_unknown_stem_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            StemsConfig(
                entries=[
                    StemEntry(
                        id=0,
                        settings=StemSettings(
                            channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])
                        ),
                    )
                ],
                hierarchy=StemsHierarchy(levels=[[0], [5]]),
            )


class TestStemsConfigViews:
    def test_entries_are_keyed_by_their_id(self) -> None:
        stems = _stems_config()
        assert set(stems.entries_by_id) == {0, 1}
        assert stems.entries_by_id[1].settings.channels == [ChannelName.NOISE]

    def test_covered_channels_gather_every_entry(self) -> None:
        stems = _stems_config()
        assert stems.covered_channels == frozenset({ChannelName.PULSE1, ChannelName.NOISE})


class TestWithoutEntries:
    """The entries a setup lets go of leave with their places in the hierarchy."""

    @staticmethod
    def _shared_level() -> StemsConfig:
        """Stems 0 and 1 picking together on the first level, stem 2 alone on the second."""
        return StemsConfig(
            entries=[
                StemEntry(
                    id=stem_id,
                    settings=StemSettings(channels=[ChannelName.PULSE1], bends=bending_channels([ChannelName.PULSE1])),
                )
                for stem_id in (0, 1, 2)
            ],
            hierarchy=StemsHierarchy(levels=[[0, 1], [2]], mode=HierarchyMode.STRICT),
        )

    def test_the_entries_named_leave(self) -> None:
        remaining = self._shared_level().without_entries(frozenset({1}))

        assert [entry.id for entry in remaining.entries] == [0, 2]
        assert remaining.hierarchy.levels == [[0], [2]]

    def test_a_level_they_empty_collapses(self) -> None:
        remaining = self._shared_level().without_entries(frozenset({2}))

        assert remaining.hierarchy.levels == [[0, 1]]

    def test_the_picking_mode_stays(self) -> None:
        remaining = self._shared_level().without_entries(frozenset({0, 1}))

        assert remaining.hierarchy.mode == HierarchyMode.STRICT
        assert remaining.hierarchy.levels == [[2]]

    def test_naming_nothing_leaves_the_setup_as_it_stands(self) -> None:
        setup = self._shared_level()

        assert setup.without_entries(frozenset()) == setup


class TestSingleEntry:
    def test_names_one_stem_over_the_settings_it_is_given(self) -> None:
        settings = StemSettings.covering([ChannelName.PULSE1, ChannelName.TRIANGLE])
        stems = StemsConfig.single_entry(settings)

        assert [entry.settings for entry in stems.entries] == [settings]
        assert stems.hierarchy.levels == [[0]]
        assert stems.covered_channels == settings.channel_set

    def test_carries_the_count_the_settings_state(self) -> None:
        settings = StemSettings.covering([ChannelName.PULSE1, ChannelName.TRIANGLE]).with_channel_cap(1)
        stems = StemsConfig.single_entry(settings)
        assert stems.entries[0].settings.channel_cap == 1
