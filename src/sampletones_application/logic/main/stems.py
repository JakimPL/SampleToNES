from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, FrozenSet, List, Optional, Self, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy

Level = Tuple["StemSource", ...]


@dataclass(frozen=True)
class StemSource:
    """One recording in a stems conversion, together with the channels it may take."""

    path: Path
    channels: FrozenSet[ChannelName]

    def with_channels(self, channels: FrozenSet[ChannelName]) -> Self:
        return replace(self, channels=channels)


@dataclass(frozen=True)
class ConversionSetup:
    """What a stems conversion runs with: the recordings it mixes and the setup handing out channels.

    Both sides are built from one pass over the levels, so the entry ids the assignment records
    name the recordings in the order the job mixes them.
    """

    sources: Tuple[Path, ...]
    stems: StemsConfig


@dataclass(frozen=True)
class StemLevels:
    """The recordings a stems conversion gathers, in the precedence levels they pick on.

    A level holds the recordings that compete on cost; the levels pick in the order they are
    listed. Position within a level is the order the entries are numbered in, which is what
    settles a tie between two equal-cost choices. Every gesture answers with a new value whose
    levels are all occupied, so the bands a reader sees stay consecutive.
    """

    levels: Tuple[Level, ...] = ()

    @classmethod
    def of(cls, levels: Sequence[Sequence[StemSource]]) -> Self:
        """Builds a value from levels given in any shape, leaving out the ones holding nothing."""
        return cls(levels=tuple(tuple(level) for level in levels if level))

    @property
    def sources(self) -> Tuple[StemSource, ...]:
        """Every recording, in the order it is mixed and numbered."""
        return tuple(source for level in self.levels for source in level)

    @property
    def paths(self) -> Tuple[Path, ...]:
        return tuple(source.path for source in self.sources)

    @property
    def count(self) -> int:
        return len(self.sources)

    @property
    def level_count(self) -> int:
        return len(self.levels)

    def holds(self, path: Path) -> bool:
        return any(source.path == path for source in self.sources)

    def level_of(self, path: Path) -> int:
        """The level the recording picks on, counted from the first."""
        for level_index, level in enumerate(self.levels):
            if any(source.path == path for source in level):
                return level_index

        raise KeyError(f"{path} is not gathered in this conversion")

    def position_of(self, path: Path) -> int:
        """The place the recording takes among the ones sharing its level."""
        level = self.levels[self.level_of(path)]
        return next(index for index, source in enumerate(level) if source.path == path)

    def add(self, source: StemSource) -> Self:
        """Gathers another recording, on the level the first recordings picked on."""
        if self.holds(source.path):
            return self

        levels = self._mutable()
        if not levels:
            return self.of([[source]])

        levels[0].append(source)
        return self.of(levels)

    def remove(self, path: Path) -> Self:
        """Lets a recording go, together with the level it emptied."""
        return self.of(self._without(path))

    def replace_source(self, path: Path, change: Callable[[StemSource], StemSource]) -> Self:
        """Rewrites one recording where it stands, leaving the rest of the setup as it is."""
        return self.of(
            [[change(source) if source.path == path else source for source in level] for level in self.levels]
        )

    def keep_first(self) -> Self:
        """Keeps the recording that picks first, which is the one a classic conversion carries."""
        sources = self.sources
        return self.of([[sources[0]]]) if sources else self.of([])

    def move_within_level(self, path: Path, offset: int) -> Self:
        """Moves a recording past the neighbour it shares a level with, changing which of them ties first."""
        source = self._source(path)
        if source is None:
            return self

        level_index = self.level_of(path)
        position = self.position_of(path) + offset
        level = list(self.levels[level_index])
        if not 0 <= position < len(level):
            return self

        level.remove(source)
        level.insert(position, source)
        levels = self._mutable()
        levels[level_index] = level
        return self.of(levels)

    def join_level(self, path: Path, offset: int) -> Self:
        """Sends a recording to the neighbouring level, where it picks with that level's recordings."""
        source = self._source(path)
        if source is None:
            return self

        target = self.level_of(path) + offset
        if not 0 <= target < self.level_count:
            return self

        levels = self._without(path)
        levels[target].append(source)
        return self.of(levels)

    def isolate(self, path: Path) -> Self:
        """Gives a recording a level of its own, picking directly after the one it shared."""
        source = self._source(path)
        if source is None or len(self.levels[self.level_of(path)]) == 1:
            return self

        levels = self._without(path)
        levels.insert(self.level_of(path) + 1, [source])
        return self.of(levels)

    def move_onto(self, path: Path, target_path: Path) -> Self:
        """Moves a recording to the level and the place another one holds."""
        source = self._source(path)
        if source is None or path == target_path or not self.holds(target_path):
            return self

        levels = self._without(path)
        for level in levels:
            for position, candidate in enumerate(level):
                if candidate.path == target_path:
                    level.insert(position, source)
                    return self.of(levels)

        return self

    def move_to_new_level(self, path: Path, position: int) -> Self:
        """Gives a recording a level of its own, in the slot the levels are broken at.

        ``position`` counts the gaps a reader sees: zero is above the first level and the level
        count is below the last, so the slot names itself the same way whichever level the
        recording is leaving.
        """
        source = self._source(path)
        if source is None:
            return self

        level_index = self.level_of(path)
        levels = self._without(path)
        target = position
        if not levels[level_index]:
            del levels[level_index]
            target = position - 1 if position > level_index else position
            if target == level_index:
                return self

        levels.insert(target, [source])
        return self.of(levels)

    def _source(self, path: Path) -> Optional[StemSource]:
        return next((source for source in self.sources if source.path == path), None)

    def _mutable(self) -> List[List[StemSource]]:
        return [list(level) for level in self.levels]

    def _without(self, path: Path) -> List[List[StemSource]]:
        """The levels with one recording taken out, keeping a level it emptied for the callers that count on it."""
        return [[source for source in level if source.path != path] for level in self.levels]


def effective_channels(
    source: StemSource,
    enabled_channels: Sequence[ChannelName],
) -> List[ChannelName]:
    """The channels a source may take in the run being set up, in the order the run enables them.

    A source keeps whichever of its channels the configuration still enables. One left holding
    none takes no part in the conversion, which is what unticking every channel of a row says.
    """
    return [channel_name for channel_name in enabled_channels if channel_name in source.channels]


def derive_conversion_setup(
    levels: StemLevels,
    enabled_channels: Sequence[ChannelName],
    *,
    channel_cap: int,
    hierarchy_mode: HierarchyMode,
) -> ConversionSetup:
    """Turns the levels a reader gathered into the recordings and the setup a conversion runs with.

    Recordings holding no enabled channel take no part, so they reach neither the mix nor the
    entries. What remains is numbered in list order, which is the id the conversion records per
    frame and a stem selection later reads back.
    """
    taking_part = [
        [(source, effective_channels(source, enabled_channels)) for source in level] for level in levels.levels
    ]
    playing = [[pair for pair in level if pair[1]] for level in taking_part]
    ordered = [pair for level in playing if level for pair in level]

    entries = [StemEntry(id=stem_id, channels=channels) for stem_id, (_source, channels) in enumerate(ordered)]
    return ConversionSetup(
        sources=tuple(source.path for source, _channels in ordered),
        stems=StemsConfig(
            entries=entries,
            hierarchy=_hierarchy(playing, hierarchy_mode),
            channel_cap=channel_cap,
        ),
    )


def _hierarchy(
    playing: Sequence[Sequence[Tuple[StemSource, List[ChannelName]]]],
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
