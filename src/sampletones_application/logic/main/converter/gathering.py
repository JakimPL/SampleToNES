from dataclasses import dataclass, replace
from pathlib import Path
from typing import FrozenSet, Optional, Self, Tuple

from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.levels import MixLevels
from sampletones_application.logic.main.sources.list import SourceList
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.slots import SettingsSlot
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class Gathering:
    """The sources a reader gathered, and the order the ones a mix converts pick in.

    The list holds whatever was gathered — recordings named one by one, folders standing for the
    recordings below them — and says what each converts under. A run that writes one reconstruction
    per recording converts the list as it stands, so the list is unbounded: a folder of thousands is
    the case that run exists for.

    The levels are the mix's side. They name the recordings one reconstruction is built from, in
    the order those recordings pick in, and there are only ever as many as a mix can hold. A mix
    converts loose recordings alone, so turning to one flattens the folders standing in the list.
    """

    sources: SourceList
    levels: MixLevels

    @classmethod
    def empty(cls) -> Self:
        """The setup a converter opens with, which a reader fills by gathering sources."""
        return cls(sources=SourceList(), levels=MixLevels())

    @property
    def count(self) -> int:
        """How many recordings the list holds, folders counting for what they stand for."""
        return self.sources.count

    @property
    def row_count(self) -> int:
        """How many rows the list draws, a folder standing as one."""
        return self.sources.row_count

    @property
    def room(self) -> int:
        """How many more recordings the mix has room to take."""
        return self.levels.room

    @property
    def paths(self) -> Tuple[Path, ...]:
        """Where every gathered recording stands, in the order the list holds it."""
        return self.sources.paths

    @property
    def recordings(self) -> Tuple[Recording, ...]:
        """Every gathered recording, in the order the list holds it."""
        return self.sources.recordings

    def recording(self, path: Path) -> Optional[Recording]:
        """The gathered recording at ``path``, where the list holds one."""
        return self.sources.recording(path)

    def folder_root_of(self, path: Path) -> Optional[Path]:
        """The folder a gathered recording was found below, where one stands for it."""
        return self.sources.folder_root_of(path)

    def listing(self, recording: Recording) -> Self:
        """One more recording in the list, which a per-recording run converts as it stands."""
        return replace(self, sources=self.sources.add_recording(recording))

    def listing_folder(self, folder: Folder) -> Self:
        """One more folder in the list, standing for every recording gathered below it."""
        return replace(self, sources=self.sources.add_folder(folder))

    def mixing(self, recording: Recording) -> Self:
        """One more recording in the list and in the mix, where the mix has room for it.

        A mix reaches a fixed number of recordings, so a setup with no room left stands as it is;
        a path already gathered keeps the settings and the place it has.
        """
        if not self.room:
            return self

        return replace(
            self,
            sources=self.sources.add_recording(recording),
            levels=self.levels.add(recording.path),
        )

    def remove(self, key: SourceKey) -> Self:
        """The setup without the row ``key`` names, which leaves the list and the mix alike."""
        sources = self.sources.remove(key)
        standing = frozenset(sources.paths)
        levels = self.levels
        for path in self.levels.paths:
            if path not in standing:
                levels = levels.remove(path)

        return replace(self, sources=sources, levels=levels)

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

    def settled(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channel_name: ChannelName,
        held: bool,
    ) -> Self:
        """The setup with ``channel_name`` settled on every recording ``key`` stands for."""
        return replace(self, sources=self.sources.settled(key, slot, channel_name, held))

    def toggled_throughout(self, slot: SettingsSlot, channel_name: ChannelName) -> Self:
        """The setup with ``channel_name`` settled the one way on every recording listed."""
        return replace(self, sources=self.sources.toggled_throughout(slot, channel_name))

    def with_levels(self, levels: MixLevels) -> Self:
        """The setup as rewritten levels leave it, the recordings standing as they were."""
        return replace(self, levels=levels)

    def mixing_only(self, recordings: Tuple[Recording, ...]) -> Self:
        """The setup a mix runs from: exactly these recordings, loose, in the order they are named.

        This is what answering for a mix leaves behind — the folders give up the recordings they
        stood for, and what the reader did not name goes with them. A recording is handed in whole
        rather than by path, so one the list already holds keeps what it was given and one joining
        from a folder arrives under the settings a recording joins with.
        """
        sources = SourceList()
        levels = MixLevels()
        for recording in recordings:
            sources = sources.add_recording(recording)
            levels = levels.add(recording.path)

        return replace(self, sources=sources, levels=levels)

    def unmixed(self) -> Self:
        """The setup a per-recording run converts: the list as it stands, the mix let go."""
        return replace(self, levels=MixLevels())
