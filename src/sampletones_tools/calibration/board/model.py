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


class BoardRow(BaseModel):
    """One reference sound across every column of a group.

    Attributes:
        item: The corpus item's name.
        category: The corpus category the item belongs to.
        recording: The page's reference to the recording every cell reconstructs.
        cells: One cell per column, in the columns' order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    item: str
    category: str
    recording: str
    cells: Tuple[BoardCell, ...]


class BoardGroup(BaseModel):
    """One table of the page: the columns it holds side by side, and the sounds they reconstruct.

    Attributes:
        name: What the group is called on its tab; empty where the page holds one group.
        columns: The column headings, in the order the cells follow.
        rows: One row per reference sound.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    columns: Tuple[str, ...]
    rows: Tuple[BoardRow, ...]


class BoardPage(BaseModel):
    """Everything the page draws, ready to be written as the data file it reads.

    Attributes:
        title: The heading the page carries.
        referee: The name of the referee whose scores the cells report.
        colors: The palette token each channel's color stands under, by channel name.
        groups: The tables the page holds, one per tab.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    referee: str
    colors: Dict[str, str]
    groups: Tuple[BoardGroup, ...]
