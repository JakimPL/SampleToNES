from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Optional, Tuple

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.sources.row import SourceRow
from sampletones_application.logic.main.sources.slots import (
    ALL_CHANNELS,
    CHANNEL_SLOT,
    SETTINGS_SLOTS,
    SettingsSlot,
)
from sampletones_application.view_model.main.converter import ConversionPhase, ConverterViewModel
from sampletones_application.view_model.main.reconstructor import (
    InspectedSourceViewModel,
    SettingsSlotViewModel,
)
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


def compose_view(
    state: ConverterState,
    *,
    phase: ConversionPhase,
    status_text: str,
    action_label: str,
    progress: float,
    running_input: Optional[Path],
    reconstructions_directory: Path,
    other_operation_active: bool,
    rows: Tuple[StemRowViewModel, ...],
) -> ConverterViewModel:
    """The panel's whole reading of the converter at one moment.

    ``running_input`` is the recording a batch is on, which stands in for what the reader gathered
    while a run is under way; ``reconstructions_directory`` is where a converter that has gathered
    nothing yet would write. ``rows`` are the gathered sources as :func:`stem_rows` last read
    them, which stand for as long as the gathering does and are therefore read once a gesture
    rather than once a progress report.
    """
    settings = state.settings
    destination = state.destination
    return ConverterViewModel(
        phase=phase,
        status_text=status_text,
        action_label=action_label,
        progress=progress,
        input_path=running_input if running_input is not None else destination.input_path,
        output_path=_display_output(destination, reconstructions_directory),
        is_file=destination.is_file,
        other_operation_active=other_operation_active,
        output=settings.output,
        stem_sources=rows,
        channel_cap=settings.effective_channel_cap,
        max_channel_cap=settings.max_channel_cap,
        hierarchy_mode=settings.hierarchy_mode,
        max_sources=MAX_STEM_SOURCES,
        selected_key=_selected_key(state),
    )


def settings_slots(state: ConverterState) -> Tuple[SettingsSlotViewModel, ...]:
    """The choices the settings card edits, read through the recordings the picked row stands for.

    With no row picked the card has nothing to answer for, so every choice offers no channel and
    the card says which gesture picks one.
    """
    inspected = inspected_settings(state)
    return tuple(_slot_reading(slot, inspected) for slot in SETTINGS_SLOTS)


def inspected_settings(state: ConverterState) -> Tuple[StemSettings, ...]:
    """The settings the card is editing, read from the recordings the picked row stands for."""
    selected = state.selected
    if selected is None:
        return ()

    row = state.gathering.sources.row(selected)
    if row is None:
        return ()

    return tuple(recording.settings for recording in row.recordings)


def inspected_source(state: ConverterState) -> Optional[InspectedSourceViewModel]:
    """The row the card is editing, named the way the list names it."""
    selected = state.selected
    if selected is None:
        return None

    row = state.gathering.sources.row(selected)
    if row is None:
        return None

    return InspectedSourceViewModel(
        name=selected.path.name if selected.names_folder else selected.path.stem,
        kind=selected.kind,
        holds=row.count,
    )


def _slot_reading(
    slot: SettingsSlot,
    inspected: Tuple[StemSettings, ...],
) -> SettingsSlotViewModel:
    offered = frozenset().union(*(slot.offered(settings) for settings in inspected)) if inspected else frozenset()
    held = set()
    partial = set()
    for channel_name in offered:
        agreement = Agreement.over(channel_name in slot.read(settings) for settings in inspected)
        if agreement is Agreement.ALL:
            held.add(channel_name)
        elif agreement is Agreement.SOME:
            partial.add(channel_name)

    return SettingsSlotViewModel(
        field=slot.field,
        offered_channels=offered,
        held_channels=frozenset(held),
        partial_channels=frozenset(partial),
    )


def _selected_key(state: ConverterState) -> Optional[str]:
    """The row a reader is inspecting, as the list names it."""
    return None if state.selected is None else str(state.selected.path)


def stem_rows(
    gathering: Gathering,
    *,
    mixes: bool,
) -> Tuple[StemRowViewModel, ...]:
    """The gathered sources as the panel reads them, each stating where it stands.

    A row is named by its path, so the list reports every gesture under the path it landed on, and
    it offers a box on every channel, since the channels a row holds are the whole of what its
    reconstruction reaches. A source that has left the disk since it was gathered reports itself as
    missing. A mix bands its recordings by the level each picks on; a run writing one reconstruction
    apiece draws one band holding the whole list, folders included.
    """
    placements = _mixed_placements(gathering) if mixes else _listed_placements(gathering)
    return tuple(_row(placement) for placement in placements)


@dataclass(frozen=True)
class _Placement:
    """One source and where it stands in the list the panel draws."""

    source: SourceRow
    path: Path
    level: int
    position: int
    level_size: int
    level_count: int


def _row(placement: _Placement) -> StemRowViewModel:
    source = placement.source
    key = source.key
    channels, partial = _readings(source)
    return StemRowViewModel(
        key=str(placement.path),
        kind=key.kind,
        path=placement.path,
        held=_held(placement) if key.names_folder else (),
        channels=channels,
        partial_channels=partial,
        offered_channels=ALL_CHANNELS,
        available=placement.path.is_dir() if key.names_folder else placement.path.is_file(),
        level=placement.level,
        position=placement.position,
        level_size=placement.level_size,
        level_count=placement.level_count,
    )


def _held(placement: _Placement) -> Tuple[StemRowViewModel, ...]:
    """The recordings a folder stands for, each answering for itself.

    They stand where the folder stands, since the folder is the row the list holds them under, and
    each reads on a channel the way a recording does — plainly ticked or clear.
    """
    return tuple(
        StemRowViewModel(
            key=str(recording.path),
            kind=recording.key.kind,
            path=recording.path,
            held=(),
            channels=frozenset(CHANNEL_SLOT.read(recording.settings)),
            partial_channels=frozenset(),
            offered_channels=ALL_CHANNELS,
            available=recording.path.is_file(),
            level=placement.level,
            position=placement.position,
            level_size=placement.level_size,
            level_count=placement.level_count,
        )
        for recording in placement.source.recordings
    )


def _readings(source: SourceRow) -> Tuple[FrozenSet[ChannelName], FrozenSet[ChannelName]]:
    """How the recordings a row stands for read on each channel.

    A channel every one of them holds is ticked, one some of them hold is half-lit, and the rest
    are clear — which for a single recording is the plain ticked-or-clear reading.
    """
    held = set()
    partial = set()
    for channel_name in ALL_CHANNELS:
        agreement = Agreement.over(
            channel_name in CHANNEL_SLOT.read(recording.settings) for recording in source.recordings
        )
        if agreement is Agreement.ALL:
            held.add(channel_name)
        elif agreement is Agreement.SOME:
            partial.add(channel_name)

    return frozenset(held), frozenset(partial)


def _mixed_placements(gathering: Gathering) -> Tuple[_Placement, ...]:
    levels = gathering.levels
    return tuple(
        _Placement(
            source=recording,
            path=path,
            level=level_index,
            position=position,
            level_size=len(level),
            level_count=levels.level_count,
        )
        for level_index, level in enumerate(levels.levels)
        for position, path in enumerate(level)
        for recording in (gathering.recording(path),)
        if recording is not None
    )


def _listed_placements(gathering: Gathering) -> Tuple[_Placement, ...]:
    rows = gathering.sources.rows
    return tuple(
        _Placement(
            source=source,
            path=source.key.path,
            level=0,
            position=position,
            level_size=len(rows),
            level_count=1,
        )
        for position, source in enumerate(rows)
    )


def _display_output(destination: Destination, reconstructions_directory: Path) -> Path:
    return destination.output_path if destination.output_path is not None else reconstructions_directory
