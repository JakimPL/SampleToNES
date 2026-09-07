from pathlib import Path
from typing import List, Sequence, Tuple

from sampletones_application.logic.main.sources.derive import derive_conversion_setup
from sampletones_application.logic.main.sources.levels import MixLevels
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.logic.main.sources.factories import recording


def _path(name: str) -> Path:
    return Path(f"/audio/{name}.wav")


def _gathered(
    *levels: Sequence[str],
    holding: Sequence[ChannelName] = (ChannelName.PULSE1,),
) -> Tuple[SourceList, MixLevels]:
    """A list and the levels naming it, every recording holding the same channels."""
    sources = SourceList()
    for level in levels:
        for name in level:
            sources = sources.add_recording(recording(str(_path(name)), holding))

    return sources, MixLevels.of([[_path(name) for name in level] for level in levels])


class TestWhatEachRecordingBringsToTheSetup(BaseTestSuite):
    def test_a_recording_carries_the_channels_its_own_row_holds(self) -> None:
        sources, levels = _gathered(["lead"], holding=[ChannelName.PULSE1, ChannelName.PULSE2])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.stems.entries[0].settings.channels == [ChannelName.PULSE1, ChannelName.PULSE2]

    def test_a_bend_the_recording_carries_reaches_the_entry(self) -> None:
        sources = SourceList().add_recording(
            recording(str(_path("lead")), [ChannelName.TRIANGLE], [ChannelName.TRIANGLE])
        )
        levels = MixLevels.of([[_path("lead")]])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.stems.entries[0].settings.bends == [ChannelName.TRIANGLE]


class TestTheSetupTheLevelsAmountTo(BaseTestSuite):
    def test_a_recordings_position_is_its_stem_id(self) -> None:
        sources, levels = _gathered(["a", "b"])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert [entry.id for entry in setup.stems.entries] == [0, 1]

    def test_recordings_sharing_a_level_pick_together(self) -> None:
        sources, levels = _gathered(["a", "c"], ["b"])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.stems.hierarchy.levels == [[0, 1], [2]]

    def test_the_mix_lists_the_recordings_in_entry_order(self) -> None:
        sources, levels = _gathered(["a"], ["b"])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        )

        assert setup.sources == (_path("a"), _path("b"))

    def test_the_cap_and_the_mode_travel_with_the_setup(self) -> None:
        sources, levels = _gathered(["a"])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=2,
            hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        )

        assert (setup.stems.channel_cap, setup.stems.hierarchy.mode) == (2, HierarchyMode.ROUND_ROBIN)


class TestARecordingThatTakesNoPart(BaseTestSuite):
    """A recording left holding no channel the run enables reaches neither the mix nor the entries."""

    def _silent_beside(self, names: List[str]) -> Tuple[SourceList, MixLevels]:
        sources = SourceList()
        for name in names:
            channels = [] if name == "silent" else [ChannelName.PULSE1]
            sources = sources.add_recording(recording(str(_path(name)), channels))

        return sources, MixLevels.of([[_path(name)] for name in names])

    def test_it_reaches_neither_the_mix_nor_the_entries(self) -> None:
        sources = SourceList()
        sources = sources.add_recording(recording(str(_path("a")), [ChannelName.PULSE1]))
        sources = sources.add_recording(recording(str(_path("silent")), []))
        sources = sources.add_recording(recording(str(_path("b")), [ChannelName.PULSE1]))
        levels = MixLevels.of([[_path("a"), _path("silent")], [_path("b")]])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.sources == (_path("a"), _path("b"))
        assert setup.stems.hierarchy.levels == [[0], [1]]

    def test_a_level_left_with_nobody_taking_part_drops_out(self) -> None:
        sources, levels = self._silent_beside(["silent", "b"])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.stems.hierarchy.levels == [[0]]

    def test_a_path_the_list_never_gathered_takes_no_part(self) -> None:
        sources, levels = _gathered(["a"])
        levels = MixLevels.of([[_path("a"), _path("stranger")]])

        setup = derive_conversion_setup(
            sources,
            levels,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.sources == (_path("a"),)
