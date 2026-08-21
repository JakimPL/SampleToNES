from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, FrozenSet, List, Self, Sequence

from sampletones_application.constants.conversion import DEFAULT_STEM_LEVEL
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


@dataclass(frozen=True)
class StemSource:
    """One row of a stems conversion: a recording, the channels it may take, and when it picks.

    The level orders the picking: every source on the lowest level chooses before any source on
    the next, which is how a reader puts a lead ahead of a pad.
    """

    path: Path
    channels: FrozenSet[ChannelName]
    level: int = DEFAULT_STEM_LEVEL

    def with_channels(self, channels: FrozenSet[ChannelName]) -> Self:
        return replace(self, channels=channels)

    def with_level(self, level: int) -> Self:
        return replace(self, level=level)


def effective_channels(
    source: StemSource,
    enabled_channels: Sequence[ChannelName],
) -> List[ChannelName]:
    """The channels a source may take in the run being set up, in the order the run enables them.

    A source keeps whichever of its channels the configuration still enables. One left holding
    none takes every enabled channel, so a source always has somewhere to sound.
    """
    kept = [channel_name for channel_name in enabled_channels if channel_name in source.channels]
    return kept if kept else list(enabled_channels)


def derive_stems_config(
    sources: Sequence[StemSource],
    enabled_channels: Sequence[ChannelName],
    *,
    channel_cap: int,
    hierarchy_mode: HierarchyMode,
) -> StemsConfig:
    """Turns the rows a reader set up into the stems setup a conversion runs under.

    A row's position in the list is its stem id, which is what the conversion records per frame
    and what a stem selection later reads back. Rows sharing a level pick together, and the
    levels follow their numbers upwards.
    """
    return StemsConfig(
        entries=[
            StemEntry(id=stem_id, channels=effective_channels(source, enabled_channels))
            for stem_id, source in enumerate(sources)
        ],
        hierarchy=_hierarchy(sources, hierarchy_mode),
        channel_cap=channel_cap,
    )


def _hierarchy(
    sources: Sequence[StemSource],
    hierarchy_mode: HierarchyMode,
) -> StemsHierarchy:
    grouped: Dict[int, List[int]] = defaultdict(list)
    for stem_id, source in enumerate(sources):
        grouped[source.level].append(stem_id)

    return StemsHierarchy(
        levels=[grouped[level] for level in sorted(grouped)],
        mode=hierarchy_mode,
    )
