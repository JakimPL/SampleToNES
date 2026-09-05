from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Dict, FrozenSet, Optional, Self, Tuple

from sampletones_application.logic.main.sources.agreement import Agreement
from sampletones_application.logic.main.sources.folder import Folder
from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.recording import Recording
from sampletones_application.logic.main.sources.row import SourceRow
from sampletones_application.logic.main.sources.slots import SettingsSlot
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


@dataclass(frozen=True)
class SourceList:
    """The rows a reader gathered a run from, in the order they were added.

    A row is one recording the reader named, or a folder standing for every recording gathered
    below it, and both kinds share the one order. A path stands here once: a folder takes over the
    loose recordings it covers, carrying the settings they already had, and a recording another
    folder holds stays where it is.

    The list holds whatever a reader gathers, a folder of thousands included. What a single mix
    may hold is the mix's own ceiling rather than this one's, since a list of that size is exactly
    what a run writing one reconstruction per recording is for.
    """

    rows: Tuple[SourceRow, ...] = ()

    @property
    def recordings(self) -> Tuple[Recording, ...]:
        """Every recording the list stands for, folders walked through to what they hold.

        This is the one reading that goes from rows to recordings; whoever needs the recordings a
        run converts asks for them here.
        """
        return tuple(recording for row in self.rows for recording in row.recordings)

    @property
    def paths(self) -> Tuple[Path, ...]:
        return tuple(recording.path for recording in self.recordings)

    @property
    def count(self) -> int:
        """How many recordings the list stands for."""
        return sum(row.count for row in self.rows)

    @property
    def row_count(self) -> int:
        """How many rows a reader sees, a folder counting as the one row it draws."""
        return len(self.rows)

    def holds(self, path: Path) -> bool:
        return any(recording.path == path for recording in self.recordings)

    def recording(self, path: Path) -> Optional[Recording]:
        return next((recording for recording in self.recordings if recording.path == path), None)

    def row(self, key: SourceKey) -> Optional[SourceRow]:
        return next((row for row in self.rows if row.key == key), None)

    def folder_root_of(self, path: Path) -> Optional[Path]:
        """The root of the folder holding ``path``, which is the tree a run mirrors for it.

        A recording the reader named answers with nothing, and its reconstruction sits directly in
        the directory the run's settings are named after.
        """
        for row in self.rows:
            if row.key.names_folder and any(recording.path == path for recording in row.recordings):
                return row.key.path

        return None

    def add_recording(self, recording: Recording) -> Self:
        """Gathers one recording the reader named, leaving a path already standing as it is."""
        if self.holds(recording.path):
            return self

        return replace(self, rows=self.rows + (recording,))

    def add_folder(self, folder: Folder) -> Self:
        """Gathers ``folder``, taking over the loose recordings it covers.

        A loose recording the folder lists joins it holding the settings it already had, so what a
        reader settled before gathering stands. A recording another folder holds stays there, which
        is what keeps every path standing in the list once.
        """
        if self.row(folder.key) is not None:
            return self

        gathered = self._gathered_by(folder)
        taken = frozenset(recording.path for recording in gathered)
        kept = tuple(row for row in self.rows if row.key.names_folder or row.key.path not in taken)
        return replace(self, rows=kept + (folder.with_recordings(gathered),))

    def remove(self, key: SourceKey) -> Self:
        """Lets go of what ``key`` names: a whole folder, or one recording wherever it stands.

        A folder goes together with every recording it holds, and a folder left holding nothing
        goes as well, since it stands for nothing a run would write.
        """
        if key.names_folder:
            return replace(self, rows=tuple(row for row in self.rows if row.key != key))

        return replace(self, rows=tuple(self._without_recording(key.path)))

    def settled(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channel_name: ChannelName,
        held: bool,
    ) -> Self:
        """The list with ``channel_name`` settled in ``slot``, on every recording ``key`` stands for.

        A folder settles by making the same edit to each recording it holds, so one gesture reads
        the same whichever kind of row answered it.
        """
        return replace(self, rows=tuple(self._settled_rows(key, slot, channel_name, held)))

    def written(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channels: FrozenSet[ChannelName],
    ) -> Self:
        """The list with ``slot`` holding exactly ``channels`` on every recording ``key`` stands for.

        This is the gesture that hands a whole reading back at once, where ``settled`` answers one
        channel at a time.
        """
        return replace(self, rows=tuple(self._rewritten_rows(key, slot, channels)))

    def toggled(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channel_name: ChannelName,
    ) -> Self:
        """The list one gesture on ``key`` leaves behind.

        A row every recording of which already makes the choice lets it go; every other reading
        settles the whole row on it, so one gesture always moves a group somewhere.
        """
        held = self.agreement(key, slot, channel_name).settles_to
        return self.settled(key, slot, channel_name, held)

    def agreement(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channel_name: ChannelName,
    ) -> Agreement:
        """How the recordings ``key`` stands for read on ``channel_name`` in ``slot``."""
        row = self.row(key)
        if row is None:
            return Agreement.NONE

        return Agreement.over(slot.holds(recording.settings, channel_name) for recording in row.recordings)

    def flattened(self) -> Self:
        """The same recordings as loose rows, in the order they stand.

        A mix converts recordings alone, so a folder standing in the list contributes what it
        holds and stops standing for them.
        """
        return replace(self, rows=self.recordings)

    def _gathered_by(self, folder: Folder) -> Tuple[Recording, ...]:
        """The recordings ``folder`` takes on, each holding the settings it already stood with."""
        loose = self._loose_recordings()
        standing = self._recordings_inside_folders()
        return tuple(
            loose.get(recording.path, recording) for recording in folder.recordings if recording.path not in standing
        )

    def _loose_recordings(self) -> Dict[Path, Recording]:
        return {
            recording.path: recording for row in self.rows if not row.key.names_folder for recording in row.recordings
        }

    def _recordings_inside_folders(self) -> FrozenSet[Path]:
        return frozenset(recording.path for row in self.rows if row.key.names_folder for recording in row.recordings)

    def _without_recording(self, path: Path) -> Tuple[SourceRow, ...]:
        rows: Tuple[SourceRow, ...] = ()
        for row in self.rows:
            if not row.key.names_folder:
                if row.key.path != path:
                    rows += (row,)
                continue

            kept = tuple(recording for recording in row.recordings if recording.path != path)
            if kept:
                rows += (Folder(root=row.key.path, recordings=kept),)

        return rows

    def _settled_rows(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channel_name: ChannelName,
        held: bool,
    ) -> Tuple[SourceRow, ...]:
        return self._rows_with(
            key,
            lambda settings: slot.settled(settings, channel_name, held),
        )

    def _rewritten_rows(
        self,
        key: SourceKey,
        slot: SettingsSlot,
        channels: FrozenSet[ChannelName],
    ) -> Tuple[SourceRow, ...]:
        return self._rows_with(key, lambda settings: slot.write(settings, channels))

    def _rows_with(
        self,
        key: SourceKey,
        change: Callable[[StemSettings], StemSettings],
    ) -> Tuple[SourceRow, ...]:
        rows: Tuple[SourceRow, ...] = ()
        for row in self.rows:
            if row.key != key:
                rows += (row,)
                continue

            changed = tuple(recording.with_settings(change(recording.settings)) for recording in row.recordings)
            if key.names_folder:
                rows += (Folder(root=key.path, recordings=changed),)
            else:
                rows += changed

        return rows
