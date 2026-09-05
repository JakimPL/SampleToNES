from pathlib import Path
from typing import List, Optional

from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_application.logic.main.converter.setup import (
    conversion_plan,
    conversion_setup,
    playing_sources,
)
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.reconstructions.converter import DirectoryConversion, GroupConversion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.unit.sampletones_application.logic.main.sources.factories import recording

JOINING: List[ChannelName] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]


def _state(
    *,
    stems_mode: bool,
    input_path: Optional[Path] = None,
    is_file: bool = True,
    gathered: Optional[List[str]] = None,
    channel_cap: int = len(JOINING),
    hierarchy_mode: HierarchyMode = DEFAULT_STEMS_HIERARCHY_MODE,
) -> ConverterState:
    gathering = Gathering.empty()
    for name in gathered or []:
        gathering = gathering.add(recording(name, JOINING))

    return ConverterState(
        settings=RunSettings(
            joining=StemSettings(channels=JOINING, bends=bending_channels(JOINING)),
            stems_mode=stems_mode,
            channel_cap=channel_cap,
            hierarchy_mode=hierarchy_mode,
        ),
        gathering=gathering,
        destination=Destination(input_path=input_path, output_path=None, is_file=is_file),
    )


class TestWhatOneConversionRuns:
    """One reconstruction for a file, one per audio file for a directory."""

    def test_a_file_becomes_one_group_over_that_file(self) -> None:
        plan = conversion_plan(_state(stems_mode=False, input_path=Path("/audio/kick.wav")))

        assert isinstance(plan, GroupConversion)
        assert plan.sources == (Path("/audio/kick.wav"),)

    def test_a_directory_becomes_a_directory_conversion(self) -> None:
        plan = conversion_plan(_state(stems_mode=False, input_path=Path("/audio"), is_file=False))

        assert isinstance(plan, DirectoryConversion)
        assert plan.directory == Path("/audio")

    def test_a_converter_aimed_at_nothing_names_no_plan(self) -> None:
        assert conversion_plan(_state(stems_mode=False)) is None

    def test_the_setup_covers_every_channel_a_recording_joins_with(self) -> None:
        """With no stems listed, one stem holds the settings a recording joins the list with."""
        state = _state(stems_mode=False, input_path=Path("/audio/kick.wav"))

        stems = conversion_setup(state).stems

        assert stems == StemsConfig.single_entry(
            JOINING,
            bending_channels(JOINING),
            channel_cap=len(JOINING),
        )
        assert stems.covered_channels == frozenset(JOINING)

    def test_the_cap_reaches_a_classic_conversion_too(self) -> None:
        """One recording per frame is a choice a reader makes for every conversion, batch included."""
        state = _state(stems_mode=False, input_path=Path("/audio/kick.wav"), channel_cap=1)

        assert conversion_setup(state).stems.channel_cap == 1


class TestWhatAMixRuns:
    def test_a_mix_groups_every_gathered_recording(self) -> None:
        plan = conversion_plan(_state(stems_mode=True, gathered=["/audio/a.wav", "/audio/b.wav"]))

        assert isinstance(plan, GroupConversion)
        assert plan.sources == (Path("/audio/a.wav"), Path("/audio/b.wav"))
        assert [entry.id for entry in plan.stems.entries] == [0, 1]

    def test_a_mix_names_its_plan_without_a_recording_ever_being_picked(self) -> None:
        """A mix converts what it gathered, so nothing about the browser's selection reaches it."""
        state = _state(stems_mode=True, gathered=["/audio/a.wav"])

        assert conversion_plan(state) is not None

    def test_the_levels_take_turns_as_the_reader_asked(self) -> None:
        state = _state(
            stems_mode=True,
            gathered=["/audio/a.wav"],
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert conversion_setup(state).stems.hierarchy.mode == HierarchyMode.STRICT

    def test_the_recordings_that_take_part_stand_in_mixing_order(self) -> None:
        state = _state(stems_mode=True, gathered=["/audio/a.wav", "/audio/b.wav"])

        assert playing_sources(state) == (Path("/audio/a.wav"), Path("/audio/b.wav"))

    def test_a_single_conversion_mixes_nobody(self) -> None:
        assert playing_sources(_state(stems_mode=False, input_path=Path("/audio/kick.wav"))) == ()
