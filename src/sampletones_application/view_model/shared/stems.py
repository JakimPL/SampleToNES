from functools import cached_property
from pathlib import Path
from typing import Dict, FrozenSet, Iterator, Optional, Self, Tuple

from pydantic import BaseModel

from sampletones_application.constants.sources import SourceKind
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName


class StemRowViewModel(BaseModel, frozen=True):
    """One row of a stems list, as the list renders it.

    A row stands for a recording or for a folder of them, and answers the same way either way:
    ``offered_channels`` names the boxes it draws, ``channels`` the ones every recording it stands
    for holds, and ``partial_channels`` the ones some of them hold. A recording reads as ticked or
    clear; a folder its recordings disagree on reads as half-lit, and one gesture settles it.

    A row states where it stands — the level it picks on, the place it takes among the recordings
    sharing that level, and how many of each the list holds — so the moves a list offers gray
    themselves out from the row alone. ``key`` is the identity the list reports a gesture under:
    the source's path where the list gathers files, the stem id where it describes a recorded
    assignment.

    ``held`` carries the recordings a folder stands for, each a row of its own, which is what a
    reader reaches by opening it. They stand where the folder stands, so a recording answers for
    itself while the folder answers for them all.

    ``bends`` names the channels whose notes the recording carries to the pitch it sounds, which a
    list recording what a finished conversion took draws beside the channel itself.
    """

    key: str
    kind: SourceKind
    path: Path
    held: Tuple["StemRowViewModel", ...]
    channels: FrozenSet[ChannelName]
    partial_channels: FrozenSet[ChannelName]
    bends: FrozenSet[ChannelName]
    offered_channels: FrozenSet[ChannelName]
    available: bool
    level: int
    position: int
    level_size: int
    level_count: int

    @property
    def holds(self) -> int:
        """How many recordings the row stands for, which a folder reads out beside its name."""
        return len(self.held)

    @property
    def recordings(self) -> Tuple["StemRowViewModel", ...]:
        """The recordings this row stands for: what a folder holds, or the row itself.

        This is the one reading that goes from a row to recordings, so whatever counts, picks or
        folds them asks here rather than telling the two kinds apart again.
        """
        return self.held or (self,)

    @property
    def bendable_channels(self) -> FrozenSet[ChannelName]:
        """The channels the row draws a bend box for: the offered ones that load a divider.

        A bend moves a note by a fraction of the divider its channel loads, so the channels
        holding one are where the choice reaches something.
        """
        return self.offered_channels & TONE_CHANNELS

    @property
    def name(self) -> str:
        """The source's own name, which is what the row reads as."""
        return self.path.name if self.stands_for_a_folder else self.path.stem

    @property
    def stands_for_a_folder(self) -> bool:
        """The row is a folder, standing for every recording gathered below it."""
        return self.kind is SourceKind.FOLDER

    @property
    def takes_part(self) -> bool:
        """The row holds a channel, so the list counts it in."""
        return bool(self.channels or self.partial_channels)

    def agreement_on(self, channel_name: ChannelName) -> Agreement:
        """How the recordings this row stands for read on ``channel_name``."""
        if channel_name in self.channels:
            return Agreement.ALL

        return Agreement.SOME if channel_name in self.partial_channels else Agreement.NONE

    @property
    def offers_channels(self) -> bool:
        """The row draws at least one box, so there is a channel to give the recording."""
        return bool(self.offered_channels)

    @property
    def in_play(self) -> bool:
        """The recording is there to be read and holds a channel, so what it carries is heard."""
        return self.available and self.takes_part

    @property
    def is_first_on_level(self) -> bool:
        return self.position == 0

    @property
    def is_last_on_level(self) -> bool:
        return self.position == self.level_size - 1

    @property
    def has_level_above(self) -> bool:
        return self.level > 0

    @property
    def has_level_below(self) -> bool:
        return self.level < self.level_count - 1

    @property
    def alone_on_level(self) -> bool:
        return self.level_size == 1


class StemsListViewModel(BaseModel, frozen=True):
    """What a stems list renders: the rows, the columns they line up in, and how they answer.

    ``muted_channels`` names the columns a choice made elsewhere has switched off, which the
    boxes report while staying as clickable as any other. ``collapse_levels`` draws every row
    in one table, leaving the levels to the reader's memory rather than to a caption.
    ``selected_key`` names the row a reader is inspecting, which the list draws picked out.
    ``picked_keys`` names the recordings standing picked where the list asks which ones to mix,
    and ``picking_room`` how many recordings that pick may hold. A list putting no such question
    names no room.
    """

    rows: Tuple[StemRowViewModel, ...]
    channels_in_play: Tuple[ChannelName, ...]
    muted_channels: FrozenSet[ChannelName]
    picked_keys: FrozenSet[str]
    picking_room: Optional[int]
    live: bool
    collapse_levels: bool
    selected_key: Optional[str]

    @classmethod
    def empty(cls) -> Self:
        """The view a list stands at before anything has been drawn into it."""
        return cls(
            rows=(),
            channels_in_play=(),
            muted_channels=frozenset(),
            picked_keys=frozenset(),
            picking_room=None,
            live=True,
            collapse_levels=False,
            selected_key=None,
        )

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def holds_folders(self) -> bool:
        """A folder stands among the rows, which is what gives the list a disclosure column."""
        return any(row.stands_for_a_folder for row in self.rows)

    @property
    def level_count(self) -> int:
        """How many levels the listed recordings are spread over."""
        return max((row.level + 1 for row in self.rows), default=0)

    def row(self, key: str) -> Optional[StemRowViewModel]:
        """The row a gesture named, where the view still holds one."""
        return self._by_key.get(key)

    def rows_on(self, level_index: int) -> Tuple[StemRowViewModel, ...]:
        """The rows one band holds, in the order they stand."""
        return tuple(row for row in self.rows if row.level == level_index)

    @property
    def recordings(self) -> Tuple[StemRowViewModel, ...]:
        """Every recording the rows stand for, folders walked through to what they hold."""
        return tuple(recording for row in self.rows for recording in row.recordings)

    def picking_of(self, row: StemRowViewModel) -> Agreement:
        """How the recordings ``row`` stands for read on standing picked.

        A folder reads the three ways its channels read: picked where every recording it holds is,
        half-lit where some are, clear where none is, so one gesture answers for the whole folder.
        """
        return Agreement.over(recording.key in self.picked_keys for recording in row.recordings)

    @property
    def picking_full(self) -> bool:
        """The pick holds all the room it has, so what stands clear waits for something to leave."""
        return self.picking_room is not None and len(self.picked_keys) >= self.picking_room

    def reaches(self, row: StemRowViewModel) -> bool:
        """Whether a click on the row's box moves it.

        A full pick answers only the rows it already holds, since taking another would build a
        reconstruction from more recordings than one is made of. Letting recordings go stays open,
        which is how a reader swaps one for another.
        """
        return not self.picking_full or self.picking_of(row) is not Agreement.NONE

    def picking_settled(self, row: StemRowViewModel) -> FrozenSet[str]:
        """The pick a click on ``row`` leaves behind.

        A row every recording of which stands picked gives them all up, and so does one the mix
        has no room to take more of; any other takes as many as the room still has, in the order
        they were gathered. So a click settles the row either way from wherever it stands, and
        half-lit is a state the reader arrives at rather than one a click makes.
        """
        if self._takes(row):
            return self.picked_keys | frozenset(self._joining(row))

        return self.picked_keys - frozenset(recording.key for recording in row.recordings)

    def _takes(self, row: StemRowViewModel) -> bool:
        """Whether a click on ``row`` brings recordings in: it settles that way, and there is room."""
        return self.picking_of(row).settles_to and not self.picking_full

    def _joining(self, row: StemRowViewModel) -> Iterator[str]:
        """The recordings a click on ``row`` takes in: its own, as far as the room left reaches."""
        standing = len(self.picked_keys)
        for recording in row.recordings:
            if recording.key in self.picked_keys:
                continue

            if self.picking_room is not None and standing >= self.picking_room:
                return

            yield recording.key
            standing += 1

    @property
    def picked_paths(self) -> Tuple[Path, ...]:
        """The recordings standing picked, in the order the list draws them."""
        return tuple(recording.path for recording in self.recordings if recording.key in self.picked_keys)

    def boxes_of(self, row: StemRowViewModel) -> Tuple[ChannelName, ...]:
        """The channels ``row`` draws a box for, in the order the columns stand."""
        return tuple(channel for channel in self.channels_in_play if channel in row.offered_channels)

    @cached_property
    def _by_key(self) -> Dict[str, StemRowViewModel]:
        """Every row a gesture can land on, the recordings inside a folder among them."""
        return {held.key: held for row in self.rows for held in (*row.held, row)}

    @property
    def playing_count(self) -> int:
        """How many of the listed recordings hold a channel."""
        return sum(1 for row in self.rows if row.takes_part)
