from dataclasses import dataclass
from typing import FrozenSet, Self, Tuple

from sampletones_application.view_model.shared.stems import StemsListViewModel
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class RowPlacement:
    """Where one row stands: what it is, which band holds it, and which boxes it draws."""

    key: str
    level: int
    offered: FrozenSet[ChannelName]


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
    def of(cls, view_model: StemsListViewModel) -> Self:
        """The shape a view amounts to, which is what a list compares against what it drew."""
        return cls(
            columns=view_model.channels_in_play,
            collapsed=view_model.collapse_levels,
            rows=tuple(
                RowPlacement(key=row.key, level=row.level, offered=row.offered_channels) for row in view_model.rows
            ),
        )

    @classmethod
    def nothing(cls) -> Self:
        """The shape a list stands at before it has drawn anything."""
        return cls(columns=(), collapsed=False, rows=())
