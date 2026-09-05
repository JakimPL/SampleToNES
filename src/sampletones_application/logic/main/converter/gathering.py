from dataclasses import dataclass, replace
from pathlib import Path
from typing import FrozenSet, Optional, Self, Tuple

from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.levels import MixLevels
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.slots import SettingsSlot
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class Gathering:
    """The recordings a mixed run is being set up from, and the order they pick in.

    The list says what each recording converts under and the levels say which of them picks first,
    so a gathered path stands in both. Holding the two together is what keeps that true through
    every gesture: one recording joins or leaves the setup in a single step, and the ceiling a mix
    holds to is answered once, before either side takes it up.
    """

    sources: SourceList
    levels: MixLevels

    @classmethod
    def empty(cls) -> Self:
        """The setup a converter opens with, which a reader fills by picking recordings."""
        return cls(sources=SourceList(), levels=MixLevels())

    @property
    def count(self) -> int:
        """How many recordings the setup holds."""
        return self.levels.count

    @property
    def room(self) -> int:
        """How many more recordings the setup has room to mix."""
        return self.levels.room

    @property
    def paths(self) -> Tuple[Path, ...]:
        """The gathered recordings, in the order they pick in."""
        return self.levels.paths

    def recording(self, path: Path) -> Optional[Recording]:
        """The gathered recording at ``path``, where the setup holds one."""
        return self.sources.recording(path)

    def add(self, recording: Recording) -> Self:
        """One more recording, picking last among the ones already gathered.

        A mix holds a fixed number of recordings, so a setup with no room left stands as it is;
        a path already gathered keeps the settings and the place it has.
        """
        if not self.room:
            return self

        return replace(
            self,
            sources=self.sources.add_recording(recording),
            levels=self.levels.add(recording.path),
        )

    def remove(self, path: Path) -> Self:
        """The setup without the recording at ``path``, which leaves both sides of it."""
        return replace(
            self,
            sources=self.sources.remove(SourceKey.recording(path)),
            levels=self.levels.remove(path),
        )

    def written(
        self,
        path: Path,
        slot: SettingsSlot,
        value: FrozenSet[ChannelName],
    ) -> Self:
        """The setup with one recording's slot settled to ``value``."""
        recording = self.recording(path)
        if recording is None:
            return self

        return replace(self, sources=self.sources.written(recording.key, slot, value))

    def written_among(
        self,
        path: Path,
        slot: SettingsSlot,
        value: FrozenSet[ChannelName],
        offered: FrozenSet[ChannelName],
    ) -> Self:
        """The setup with one recording's slot settled to ``value``, among the channels ``offered``.

        A channel left out of the run reaches no checkbox, so the recording keeps whatever it was
        given for it and gets that choice back when the channel returns.
        """
        recording = self.recording(path)
        if recording is None:
            return self

        held = slot.read(recording.settings)
        return self.written(path, slot, (held - offered) | value)

    def with_levels(self, levels: MixLevels) -> Self:
        """The setup as rewritten levels leave it, the recordings standing as they were."""
        return replace(self, levels=levels)

    def kept_first(self) -> Self:
        """What is left when a mix becomes one conversion: the recording that picks first."""
        levels = self.levels.keep_first()
        return replace(self, sources=self._narrowed_to(levels.paths), levels=levels)

    def _narrowed_to(self, standing: Tuple[Path, ...]) -> SourceList:
        """The list holding the recordings ``standing`` names, which is what a mix converts."""
        kept = frozenset(standing)
        sources = self.sources
        for path in self.sources.paths:
            if path not in kept:
                sources = sources.remove(SourceKey.recording(path))

        return sources
