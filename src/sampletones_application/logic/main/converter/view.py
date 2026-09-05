from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Optional, Tuple

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.converter.destination import Destination
from sampletones_application.logic.main.converter.gathering import Gathering
from sampletones_application.logic.main.converter.state import ConverterState
from sampletones_application.view_model.main.converter import ConversionPhase, ConverterViewModel
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

    ``running_input`` is the recording a batch is on, which stands in for what the reader picked
    while a run is under way; ``reconstructions_directory`` is where a converter that has been
    aimed at nothing yet would write.
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
    """The gathered recordings as the panel reads them, each stating where it stands.

    A gathered recording is named by its path, so the list reports every gesture under the path it
    landed on, and it offers a box on every channel the run enables. A recording that has left the
    disk since it was gathered reports itself as missing. A mix bands its recordings by the level
    each picks on; a run writing one reconstruction apiece has one band holding the whole list.
    """
    placements = _mixed_placements(gathering) if mixes else _listed_placements(gathering)
    return tuple(
        StemRowViewModel(
            key=str(placement.path),
            path=placement.path,
            channels=_held_channels(gathering, placement.path, enabled_channels),
            offered_channels=enabled_channels,
            available=placement.path.is_file(),
            level=placement.level,
            position=placement.position,
            level_size=placement.level_size,
            level_count=placement.level_count,
        )
        for placement in placements
    )


@dataclass(frozen=True)
class _Placement:
    """Where one recording stands in the list the panel draws."""

    path: Path
    level: int
    position: int
    level_size: int
    level_count: int


def _mixed_placements(gathering: Gathering) -> Tuple[_Placement, ...]:
    levels = gathering.levels
    return tuple(
        _Placement(
            path=path,
            level=level_index,
            position=position,
            level_size=len(level),
            level_count=levels.level_count,
        )
        for level_index, level in enumerate(levels.levels)
        for position, path in enumerate(level)
    )


def _listed_placements(gathering: Gathering) -> Tuple[_Placement, ...]:
    paths = gathering.paths
    return tuple(
        _Placement(
            path=path,
            level=0,
            position=position,
            level_size=len(paths),
            level_count=1,
        )
        for position, path in enumerate(paths)
    )


def _display_output(destination: Destination, reconstructions_directory: Path) -> Path:
    return destination.output_path if destination.output_path is not None else reconstructions_directory


def _held_channels(
    gathering: Gathering,
    path: Path,
    enabled_channels: FrozenSet[ChannelName],
) -> FrozenSet[ChannelName]:
    """The channels one gathered recording takes, among the ones the run enables."""
    recording = gathering.recording(path)
    return recording.settings.channel_set & enabled_channels if recording is not None else frozenset()
