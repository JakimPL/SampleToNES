from dataclasses import dataclass
from typing import FrozenSet, Self, Tuple

from sampletones_application.ui.elements.stems.expansion import OpenFolders
from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class RowPlacement:
    """Where one row stands: what it is, which band holds it, and which boxes it draws.

    ``held`` names the recordings a folder stands for, so one of them leaving reshapes the list
    the way a loose row leaving does and the region it stood in is drawn again.
    """

    key: str
    level: int
    offered: FrozenSet[ChannelName]
    opened: bool
    held: Tuple[str, ...]


@dataclass(frozen=True)
class ListShape:
    """What the bands are built from, so a change here is a rebuild and anything else a repaint.

    Which channels a row holds is drawn onto the widgets already standing, so a tick keeps the
    bands as they are and the pointer keeps whatever it was over.
    """

    columns: Tuple[ChannelName, ...]
    collapsed: bool
    rows: Tuple[RowPlacement, ...]

    @classmethod
    def of(cls, view_model: StemsListViewModel, open_folders: OpenFolders) -> Self:
        """The shape a view amounts to, which is what a list compares against what it drew.

        A folder opening or closing reshapes the list, since the region its recordings stand in
        is built and taken down with it, and so does a recording leaving the folder, since the
        region then holds a row for something the list no longer stands for.
        """
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
