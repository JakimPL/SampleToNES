from dataclasses import dataclass


@dataclass(frozen=True)
class StemsListOffer:
    """What a stems list lets a reader do with a row, which is what its owner can answer for.

    The converter's gathered recordings and a reconstruction's recorded assignment are the same
    rows drawn the same way; what differs is the gestures each owner honors. A list states that
    here, once, so a drawing step reads one declaration rather than asking a flag of its own.

    ``bends`` states that a channel's cell carries the bend on it beside the channel itself, which
    a list recording what a finished conversion took draws and a list setting a run up leaves to
    the settings card.
    """

    master_box: bool
    removal: bool
    keeps_last_row: bool
    dragging: bool
    bends: bool


GATHERED_SOURCES: StemsListOffer = StemsListOffer(
    master_box=False,
    removal=True,
    keeps_last_row=False,
    dragging=True,
    bends=False,
)

RECORDED_ASSIGNMENT: StemsListOffer = StemsListOffer(
    master_box=True,
    removal=True,
    keeps_last_row=True,
    dragging=False,
    bends=False,
)
