from dataclasses import dataclass

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_CHANNELS,
    SUF_CHECKBOX,
    SUF_FOLDER,
    SUF_GROUP,
    SUF_HANDLER_REGISTRY,
    SUF_LEVEL,
    SUF_PAYLOAD,
    SUF_REGION,
    SUF_ROW,
    SUF_TABLE,
    SUF_WELL,
)
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class StemsTags:
    """The tag grammar one stems list draws under.

    Every widget a list builds is named from the list's own prefix, so the grammar stands in one
    place and whatever addresses a row — the list, its handlers, a test — spells it the same way.
    """

    prefix: str

    @property
    def well(self) -> str:
        """The recessed region the list is drawn in, which is what an owner shows and hides."""
        return compose_tag(self.prefix, SUF_WELL)

    @property
    def body(self) -> str:
        """The group the bands are built into, which a rebuild empties."""
        return compose_tag(self.well, SUF_GROUP)

    @property
    def table(self) -> str:
        """The one table every row stands in while the levels are collapsed."""
        return compose_tag(self.prefix, SUF_TABLE)

    def segment(self, position: int) -> str:
        """One run of rows standing between two folders, each declaring the same columns.

        A folder breaks the run it stands in, so the recordings on either side of one line up in
        tables of their own; the first of them is the list's own table, and the only one a list
        holding no folder draws.
        """
        return self.table if position == 0 else compose_tag(self.table, str(position))

    def folder(self, key: str, suffix: str) -> str:
        """The tag one of an open folder's own widgets carries: its region, or the rows in it."""
        return compose_tag(self.prefix, SUF_FOLDER, key, suffix)

    def region(self, key: str) -> str:
        """The bounded space a folder's recordings scroll in while it stands open."""
        return self.folder(key, SUF_REGION)

    def held(self, key: str) -> str:
        """The table the recordings inside one open folder stand in."""
        return self.folder(key, compose_tag(SUF_REGION, SUF_TABLE))

    @property
    def payload(self) -> str:
        """The kind of payload this list's drags carry, so one list's rows land in it alone."""
        return compose_tag(self.prefix, SUF_PAYLOAD)

    def handlers(self, kind: str) -> str:
        """The registry the widgets of one kind share, which is where their hover is answered."""
        return compose_tag(self.prefix, kind, SUF_HANDLER_REGISTRY)

    def row(self, key: str, suffix: str) -> str:
        """The tag one of a row's widgets carries, which is how anything outside addresses it."""
        return compose_tag(self.prefix, SUF_ROW, key, suffix)

    def level(self, level_index: int, suffix: str) -> str:
        """The tag one of a band's widgets carries: its caption, its table, or the strip above it."""
        return compose_tag(self.prefix, SUF_LEVEL, str(level_index), suffix)

    def channel(self, key: str, channel_name: ChannelName) -> str:
        """The tag the box giving ``key`` a channel carries."""
        return compose_tag(
            self.prefix,
            SUF_ROW,
            key,
            SUF_CHANNELS,
            compose_tag(channel_name, SUF_CHECKBOX),
        )
