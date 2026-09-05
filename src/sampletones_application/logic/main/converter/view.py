from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Optional, Tuple

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.logic.main.sources.row import SourceRow
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_application.view_model.main.converter import ConversionPhase, ConverterViewModel
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_application.view_model.shared.stems import StemRowViewModel
from sampletones_core.constants.enums import ChannelName


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
) -> ConverterViewModel:
    """The panel's whole reading of the converter at one moment.

    ``running_input`` is the recording a batch is on, which stands in for what the reader gathered
    while a run is under way; ``reconstructions_directory`` is where a converter that has gathered
    nothing yet would write.
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
        stem_sources=stem_rows(state.gathering, settings.enabled_channels, mixes=settings.mixes),
        enabled_channels=settings.enabled_channels,
        channel_cap=settings.effective_channel_cap,
        max_channel_cap=settings.max_channel_cap,
        hierarchy_mode=settings.hierarchy_mode,
        max_sources=MAX_STEM_SOURCES,
    )


def stem_rows(
    gathering: Gathering,
    enabled_channels: FrozenSet[ChannelName],
    *,
    mixes: bool,
) -> Tuple[StemRowViewModel, ...]:
    """The gathered sources as the panel reads them, each stating where it stands.

    A row is named by its path, so the list reports every gesture under the path it landed on, and
    it offers a box on every channel the run enables. A source that has left the disk since it was
    gathered reports itself as missing. A mix bands its recordings by the level each picks on; a
    run writing one reconstruction apiece draws one band holding the whole list, folders included.
    """
    placements = _mixed_placements(gathering) if mixes else _listed_placements(gathering)
    return tuple(_row(placement, enabled_channels) for placement in placements)


@dataclass(frozen=True)
class _Placement:
    """One source and where it stands in the list the panel draws."""

    source: SourceRow
    path: Path
    level: int
    position: int
    level_size: int
    level_count: int


def _row(placement: _Placement, enabled_channels: FrozenSet[ChannelName]) -> StemRowViewModel:
    source = placement.source
    key = source.key
    channels, partial = _readings(source, enabled_channels)
    return StemRowViewModel(
        key=str(placement.path),
        kind=key.kind,
        path=placement.path,
        holds=source.count,
        channels=channels,
        partial_channels=partial,
        offered_channels=enabled_channels,
        available=placement.path.is_dir() if key.names_folder else placement.path.is_file(),
        level=placement.level,
        position=placement.position,
        level_size=placement.level_size,
        level_count=placement.level_count,
    )


def _readings(
    source: SourceRow,
    enabled_channels: FrozenSet[ChannelName],
) -> Tuple[FrozenSet[ChannelName], FrozenSet[ChannelName]]:
    """How the recordings a row stands for read on each channel the run enables.

    A channel every one of them holds is ticked, one some of them hold is half-lit, and the rest
    are clear — which for a single recording is the plain ticked-or-clear reading.
    """
    held = set()
    partial = set()
    for channel_name in enabled_channels:
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
