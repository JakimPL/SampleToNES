from dataclasses import dataclass


@dataclass(frozen=True)
class StemsListOffer:
    """What a stems list lets a reader do with a row, which is what its owner can answer for.

    The converter's gathered recordings, a reconstruction's recorded assignment and the question
    of which recordings to mix are the same rows drawn the same way; what differs is the gestures
    each owner honors. A list states that here, once, so a drawing step reads one declaration
    rather than asking a flag of its own.

    ``bends`` states that a channel's cell carries the bend on it beside the channel itself, which
    a list recording what a finished conversion took draws and a list setting a run up leaves to
    the settings card.

    ``picking`` states that the box beside a row picks the row for a mix rather than answering for
    its channels, which is the reading a list asking which recordings to mix draws.
    """

    master_box: bool
    removal: bool
    keeps_last_row: bool
    dragging: bool
    bends: bool
    picking: bool


GATHERED_SOURCES: StemsListOffer = StemsListOffer(
    master_box=False,
    removal=True,
    keeps_last_row=False,
    dragging=True,
    bends=False,
    picking=False,
)

RECORDED_ASSIGNMENT: StemsListOffer = StemsListOffer(
    master_box=True,
    removal=True,
    keeps_last_row=True,
    dragging=False,
    bends=False,
    picking=False,
)

PICKED_SOURCES: StemsListOffer = StemsListOffer(
    master_box=True,
    removal=False,
    keeps_last_row=False,
    dragging=False,
    bends=False,
    picking=True,
)
