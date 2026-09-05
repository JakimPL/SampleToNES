from pathlib import Path
from typing import List, Optional

from sampletones_application.constants.output import OutputKind
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.settings import RunSettings
from sampletones_application.logic.main.converter.setup import (
    batch_entries,
    conversion_plan,
    conversion_setup,
    playing_sources,
)
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_core.constants.algorithm import DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import ChannelName, HierarchyMode, bending_channels
from sampletones_core.reconstructions.converter import BatchConversion, GroupConversion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.unit.sampletones_application.logic.main.sources.factories import folder, recording

JOINING: List[ChannelName] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]


def _state(
    *,
    output: OutputKind,
    listed: Optional[List[str]] = None,
    mixed: Optional[List[str]] = None,
    gathered_folder: Optional[str] = None,
    channel_cap: int = len(JOINING),
    hierarchy_mode: HierarchyMode = DEFAULT_STEMS_HIERARCHY_MODE,
) -> ConverterState:
    gathering = Gathering.empty()
    for name in listed or []:
        gathering = gathering.listing(recording(name, JOINING))

    for name in mixed or []:
        gathering = gathering.mixing(recording(name, JOINING))

    if gathered_folder is not None:
        gathering = gathering.listing_folder(
            folder(
                gathered_folder,
                [recording(f"{gathered_folder}/a.wav", JOINING), recording(f"{gathered_folder}/b.wav", JOINING)],
            )
        )

    return ConverterState(
        settings=RunSettings(
            joining=StemSettings(channels=JOINING, bends=bending_channels(JOINING)),
            output=output,
            channel_cap=channel_cap,
            hierarchy_mode=hierarchy_mode,
        ),
        gathering=gathering,
        destination=Destination.unset(),
    )


class TestWhatAPerRecordingRunConverts:
    """One reconstruction per gathered recording, each under the settings its own row holds."""

    def test_a_recording_becomes_an_entry_of_its_own(self) -> None:
        plan = conversion_plan(_state(output=OutputKind.PER_RECORDING, listed=["/audio/kick.wav"]))

        assert isinstance(plan, BatchConversion)
        assert [entry.source for entry in plan.entries] == [Path("/audio/kick.wav")]

    def test_a_recording_the_reader_named_carries_no_folder(self) -> None:
        entries = batch_entries(_state(output=OutputKind.PER_RECORDING, listed=["/audio/kick.wav"]))

        assert entries[0].base_directory is None
        assert entries[0].is_named is True

    def test_a_recording_gathered_from_a_folder_carries_the_folder_its_tree_mirrors(self) -> None:
        entries = batch_entries(_state(output=OutputKind.PER_RECORDING, gathered_folder="/audio"))

        assert [entry.base_directory for entry in entries] == [Path("/audio"), Path("/audio")]

    def test_an_entry_holds_the_channels_the_recording_joins_with(self) -> None:
        entries = batch_entries(_state(output=OutputKind.PER_RECORDING, listed=["/audio/kick.wav"]))

        assert entries[0].stems == StemsConfig.single_entry(JOINING, [], channel_cap=len(JOINING))

    def test_the_cap_reaches_every_entry(self) -> None:
        """One recording per frame is a choice a reader makes for every conversion, batch included."""
        state = _state(output=OutputKind.PER_RECORDING, listed=["/audio/a.wav", "/audio/b.wav"], channel_cap=1)

        assert [entry.stems.channel_cap for entry in batch_entries(state)] == [1, 1]

    def test_a_setup_holding_nothing_names_no_plan(self) -> None:
        assert conversion_plan(_state(output=OutputKind.PER_RECORDING)) is None


class TestWhatAMixRuns:
    def test_a_mix_groups_every_gathered_recording(self) -> None:
        plan = conversion_plan(_state(output=OutputKind.MIXED, mixed=["/audio/a.wav", "/audio/b.wav"]))

        assert isinstance(plan, GroupConversion)
        assert plan.sources == (Path("/audio/a.wav"), Path("/audio/b.wav"))
        assert [entry.id for entry in plan.stems.entries] == [0, 1]

    def test_a_mix_with_nobody_taking_part_names_no_plan(self) -> None:
        assert conversion_plan(_state(output=OutputKind.MIXED)) is None

    def test_the_levels_take_turns_as_the_reader_asked(self) -> None:
        state = _state(
            output=OutputKind.MIXED,
            mixed=["/audio/a.wav"],
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert conversion_setup(state).stems.hierarchy.mode == HierarchyMode.STRICT

    def test_the_recordings_that_take_part_stand_in_mixing_order(self) -> None:
        state = _state(output=OutputKind.MIXED, mixed=["/audio/a.wav", "/audio/b.wav"])

        assert playing_sources(state) == (Path("/audio/a.wav"), Path("/audio/b.wav"))

    def test_a_per_recording_run_reaches_the_recordings_it_writes(self) -> None:
        state = _state(output=OutputKind.PER_RECORDING, listed=["/audio/a.wav", "/audio/b.wav"])

        assert playing_sources(state) == (Path("/audio/a.wav"), Path("/audio/b.wav"))
