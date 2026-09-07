from dataclasses import dataclass, replace
from typing import FrozenSet, List, Self, Tuple

from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class Reshape:
    """What a new reading asks of a list that has already drawn one.

    ``whole`` asks for the list afresh, which is what a change to the columns, the banding or the
    rows themselves comes to. ``folders`` names the folders whose own regions are drawn again,
    which is what a change confined to the recordings a folder stands for comes to: the rows
    around it keep the widgets they stand as, and the reader keeps the scroll they left.
    """

    whole: bool
    folders: Tuple[str, ...]

    @classmethod
    def nothing(cls) -> Self:
        """What a reading the list already stands at asks for, which a repaint answers on its own."""
        return cls(whole=False, folders=())

    @classmethod
    def everything(cls) -> Self:
        """What a reading the standing widgets cannot be brought to asks for."""
        return cls(whole=True, folders=())

    @classmethod
    def within(cls, folders: Tuple[str, ...]) -> Self:
        """What a reading that moved the recordings of these folders alone asks for."""
        return cls(whole=False, folders=folders)

    @property
    def redraws(self) -> bool:
        """Widgets are built, so whoever answers settles the regions once the frame has drawn."""
        return self.whole or bool(self.folders)


@dataclass(frozen=True)
class RowPlacement:
    """Where one row stands: what it is, which band holds it, and which boxes it draws.

    ``held`` names the recordings a folder stands for, so one of them leaving is met by the folder
    it left, and the region that folder opens onto is the only thing drawn again.
    """

    key: str
    level: int
    offered: FrozenSet[ChannelName]
    opened: bool
    held: Tuple[str, ...]

    def stands_where(self, other: Self) -> bool:
        """Both placements put the same row in the same place, whatever it now holds."""
        return replace(self, held=()) == replace(other, held=())


@dataclass(frozen=True)
class ListShape:
    """What the bands are built from, so a change here is a redraw and anything else a repaint.

    Which channels a row holds is drawn onto the widgets already standing, so a tick keeps the
    bands as they are and the pointer keeps whatever it was over.
    """

    columns: Tuple[ChannelName, ...]
    collapsed: bool
    rows: Tuple[RowPlacement, ...]

    @classmethod
    def of(cls, view_model: StemsListViewModel, open_folders: OpenFolders) -> Self:
        """The shape a view amounts to, which is what a list compares against what it drew."""
        return cls(
            columns=view_model.channels_in_play,
            collapsed=view_model.collapse_levels,
            rows=tuple(
                RowPlacement(
                    key=row.key,
                    level=row.level,
                    offered=row.offered_channels,
                    opened=open_folders.stands_open(row.key),
                    held=tuple(recording.key for recording in row.held),
                )
                for row in view_model.rows
            ),
        )

    @classmethod
    def nothing(cls) -> Self:
        """The shape a list stands at before it has drawn anything."""
        return cls(columns=(), collapsed=False, rows=())

    def against(self, standing: Self) -> Reshape:
        """What a list standing at ``standing`` is asked for to come to this shape.

        A folder opening or closing, a row arriving or leaving, and a change to the columns or the
        banding all reach the whole list, since the tables are built around them. A recording
        leaving the folder it was gathered under reaches that folder alone: the region below its
        row draws a row for each recording the folder still stands for, and the row itself reads
        out how many that is.
        """
        if self.columns != standing.columns or self.collapsed != standing.collapsed:
            return Reshape.everything()

        if len(self.rows) != len(standing.rows):
            return Reshape.everything()

        folders: List[str] = []
        for row, stood in zip(self.rows, standing.rows):
            if not row.stands_where(stood):
                return Reshape.everything()

            if row.held != stood.held:
                folders.append(row.key)

        return Reshape.within(tuple(folders))
