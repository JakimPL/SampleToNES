from typing import Dict, Tuple

from pydantic import BaseModel, ConfigDict


class BoardChannel(BaseModel):
    """One channel of a render, as the page draws and plays it.

    Attributes:
        name: The channel's own name, which its palette token is derived from.
        timeline: One character per frame, ``1`` where the channel sounds.
        solo: The page's reference to the clip holding this channel alone.
        mute: The page's reference to the clip holding every other channel.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    timeline: str
    solo: str
    mute: str


class BoardCell(BaseModel):
    """One render of one item under one column: what it scores, and what a listener may play.

    Attributes:
        render: The page's reference to the whole render.
        score: The headline referee's distance between the render and its recording.
        silence: What the same referee scores complete silence at, the distance a render closes.
        channels: The channels the render sounds, in the order the hardware holds them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    render: str
    score: float
    silence: float
    channels: Tuple[BoardChannel, ...]


class BoardRecording(BaseModel):
    """The recording the cells matched at one level reconstruct.

    Attributes:
        level: The level the recording was prepared at, which names it where a row holds several.
        clip: The page's reference to the recording.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: str
    clip: str


class BoardRow(BaseModel):
    """One reference sound across every column of a group.

    Attributes:
        item: The corpus item's name.
        family: The family the item belongs to, which the page heads its section with.
        category: The corpus category the item belongs to.
        recordings: One recording per level the cells were matched at, in the order the columns first
            reach each level, so every cell plays beside the recording at its own level.
        cells: One cell per column, in the columns' order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    item: str
    family: str
    category: str
    recordings: Tuple[BoardRecording, ...]
    cells: Tuple[BoardCell, ...]


class BoardColumn(BaseModel):
    """One column of a group: the name it stands for, and the words its heading shows.

    Attributes:
        name: The column's whole name, the label of a variant or of a run.
        words: The words of the name past the prefix every column of the group shares, one per line
            of the heading. A column named by the prefix alone holds none, as the base configuration
            the other columns add to.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    words: Tuple[str, ...]


class BoardFamily(BaseModel):
    """One family of a group, which the page draws as a card of its own.

    Attributes:
        name: The family's name, which heads its card.
        channels: Every channel a render of the family sounds, in the order the hardware holds them.
            Each cell of the family keeps a lane for every one of them, so a channel stands at one
            height across a row whichever channels each render holds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    channels: Tuple[str, ...]


class BoardGroup(BaseModel):
    """One tab of the page: the columns it holds side by side, and the sounds they reconstruct.

    Attributes:
        name: What the group is called on its tab.
        prefix: The words every column's name starts with, joined as the names join them, which the
            page states once for the group; empty where the names share none.
        columns: The columns, in the order the cells follow.
        families: One per card, in the order the rows first name them.
        rows: One row per reference sound.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    prefix: str
    columns: Tuple[BoardColumn, ...]
    families: Tuple[BoardFamily, ...]
    rows: Tuple[BoardRow, ...]


class BoardGlyphs(BaseModel):
    """The application's glyphs the page draws with.

    Attributes:
        header: The purpose glyph leading each family's card header.
        expanded: The chevron of an open card.
        collapsed: The chevron of a closed card.
        play: The glyph on the button that plays a render.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    header: str
    expanded: str
    collapsed: str
    play: str


class BoardPage(BaseModel):
    """Everything the page draws, ready to be written as the data file it reads.

    Attributes:
        title: The heading the page carries.
        referee: The name of the referee whose scores the cells report.
        glyphs: The application's glyphs the page draws with.
        colors: The role each channel's color stands under, by channel name.
        groups: The tables the page holds, one per tab.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    referee: str
    glyphs: BoardGlyphs
    colors: Dict[str, str]
    groups: Tuple[BoardGroup, ...]
