from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, List, Sequence, Tuple

from sampletones_application.logic.main.sources.levels import MixLevels
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.slots import CHANNEL_SLOT
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


@dataclass(frozen=True)
class ConversionSetup:
    """What a mixed conversion runs with: the recordings it mixes and the setup handing out channels.

    Both sides are built from one pass over the levels, so the entry ids the assignment records
    name the recordings in the order the job mixes them.
    """

    sources: Tuple[Path, ...]
    stems: StemsConfig


def derive_conversion_setup(
    sources: SourceList,
    levels: MixLevels,
    enabled_channels: AbstractSet[ChannelName],
    *,
    channel_cap: int,
    hierarchy_mode: HierarchyMode,
) -> ConversionSetup:
    """Turns the levels a reader gathered into the recordings and the setup a conversion runs with.

    Each recording is narrowed to the channels the run still enables, and one left holding none
    takes no part: it reaches neither the mix nor the entries. What remains is numbered in level
    order, which is the id the conversion records per frame and a stem selection later reads back.
    """
    playing = [_recordings_of(sources, level, enabled_channels) for level in levels.levels]
    ordered = [recording for level in playing for recording in level]

    entries = [StemEntry(id=stem_id, settings=recording.settings) for stem_id, recording in enumerate(ordered)]
    return ConversionSetup(
        sources=tuple(recording.path for recording in ordered),
        stems=StemsConfig(
            entries=entries,
            hierarchy=_hierarchy(playing, hierarchy_mode),
            channel_cap=channel_cap,
        ),
    )


def _recordings_of(
    sources: SourceList,
    level: Sequence[Path],
    enabled_channels: AbstractSet[ChannelName],
) -> List[Recording]:
    """The recordings of one level, each narrowed to the channels the run enables and still playing."""
    narrowed = []
    for path in level:
        recording = sources.recording(path)
        if recording is None:
            continue

        settings = CHANNEL_SLOT.write(recording.settings, recording.settings.channel_set & enabled_channels)
        if settings.channels:
            narrowed.append(recording.with_settings(settings))

    return narrowed


def _hierarchy(
    playing: Sequence[Sequence[Recording]],
    hierarchy_mode: HierarchyMode,
) -> StemsHierarchy:
    levels: List[List[int]] = []
    stem_id = 0
    for level in playing:
        if not level:
            continue

        levels.append([stem_id + offset for offset in range(len(level))])
        stem_id += len(level)

    return StemsHierarchy(levels=levels, mode=hierarchy_mode)
