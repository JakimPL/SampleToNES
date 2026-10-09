from dataclasses import dataclass
from pathlib import Path
from typing import List, Self, Sequence, Tuple

from sampletones_application.constants.conversion import MAX_STEM_SOURCES

Level = Tuple[Path, ...]


@dataclass(frozen=True)
class MixLevels:
    """The recordings one mixed reconstruction is built from, in the precedence levels they pick on.

    A level holds the recordings that compete on cost; the levels pick in the order they are
    listed. Position within a level is the order the entries are numbered in, which is what settles
    a tie between two equal-cost choices. Every gesture answers with a new value whose levels are
    all occupied, so the bands a reader sees stay consecutive.

    Only paths stand here. What each recording is converted with belongs to the list it was
    gathered in, so the precedence structure and the settings each have one home.

    A mix reaches at most ``MAX_STEM_SOURCES`` recordings, which is the ceiling the hardware's four
    channels and the assignment's per-frame budget leave worth mixing.
    """

    levels: Tuple[Level, ...] = ()

    @classmethod
    def of(cls, levels: Sequence[Sequence[Path]]) -> Self:
        """Builds a value from levels given in any shape, keeping the ones that hold a recording."""
        return cls(levels=tuple(tuple(level) for level in levels if level))

    @property
    def paths(self) -> Tuple[Path, ...]:
        """Every recording, in the order it is mixed and numbered."""
        return tuple(path for level in self.levels for path in level)

    @property
    def count(self) -> int:
        return len(self.paths)

    @property
    def level_count(self) -> int:
        return len(self.levels)

    @property
    def ceiling(self) -> int:
        """How many recordings one mix reaches, which is the ceiling every reader of it asks for."""
        return MAX_STEM_SOURCES

    @property
    def room(self) -> int:
        """How many more recordings this mix reaches."""
        return self.ceiling - self.count

    def holds(self, path: Path) -> bool:
        return path in self.paths

    def level_of(self, path: Path) -> int:
        """The level the recording picks on, counted from the first.

        Raises:
            KeyError: If ``path`` is gathered in no level of this mix.
        """
        for level_index, level in enumerate(self.levels):
            if path in level:
                return level_index

        raise KeyError(f"{path} is not gathered in this mix")

    def position_of(self, path: Path) -> int:
        """The place the recording takes among the ones sharing its level."""
        return self.levels[self.level_of(path)].index(path)

    def add(self, path: Path) -> Self:
        """Gathers another recording, on the level the first recordings picked on.

        A mix already at its ceiling stands as it is, so a caller reads ``room`` to know what it
        can still gather.
        """
        if self.holds(path) or not self.room:
            return self

        levels = self._mutable()
        if not levels:
            return self.of([[path]])

        levels[0].append(path)
        return self.of(levels)

    def remove(self, path: Path) -> Self:
        """Lets a recording go, together with the level it emptied."""
        return self.of(self._without(path))

    def move_within_level(self, path: Path, offset: int) -> Self:
        """Moves a recording past the neighbor it shares a level with, changing which ties first."""
        if not self.holds(path):
            return self

        level_index = self.level_of(path)
        position = self.position_of(path) + offset
        level = list(self.levels[level_index])
        if not 0 <= position < len(level):
            return self

        level.remove(path)
        level.insert(position, path)
        levels = self._mutable()
        levels[level_index] = level
        return self.of(levels)

    def join_level(self, path: Path, offset: int) -> Self:
        """Sends a recording to the neighboring level, where it picks with that level's recordings."""
        if not self.holds(path):
            return self

        target = self.level_of(path) + offset
        if not 0 <= target < self.level_count:
            return self

        levels = self._without(path)
        levels[target].append(path)
        return self.of(levels)

    def isolate(self, path: Path) -> Self:
        """Gives a recording a level of its own, picking directly after the one it shared."""
        if not self.holds(path) or len(self.levels[self.level_of(path)]) == 1:
            return self

        levels = self._without(path)
        levels.insert(self.level_of(path) + 1, [path])
        return self.of(levels)

    def move_onto(self, path: Path, target_path: Path) -> Self:
        """Moves a recording to the level and the place another one holds."""
        if not self.holds(path) or path == target_path or not self.holds(target_path):
            return self

        levels = self._without(path)
        for level in levels:
            if target_path in level:
                level.insert(level.index(target_path), path)
                return self.of(levels)

        return self

    def move_to_new_level(self, path: Path, position: int) -> Self:
        """Gives a recording a level of its own, in the slot the levels are broken at.

        ``position`` counts the gaps a reader sees: zero is above the first level and the level
        count is below the last, so the slot names itself the same way whichever level the
        recording is leaving.
        """
        if not self.holds(path):
            return self

        level_index = self.level_of(path)
        levels = self._without(path)
        target = position
        if not levels[level_index]:
            del levels[level_index]
            target = position - 1 if position > level_index else position
            if target == level_index:
                return self

        levels.insert(target, [path])
        return self.of(levels)

    def _mutable(self) -> List[List[Path]]:
        return [list(level) for level in self.levels]

    def _without(self, path: Path) -> List[List[Path]]:
        """The levels with one recording taken out, keeping a level it emptied for the callers that count on it."""
        return [[held for held in level if held != path] for level in self.levels]
