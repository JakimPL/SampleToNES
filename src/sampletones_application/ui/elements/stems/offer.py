from dataclasses import dataclass


@dataclass(frozen=True)
class StemsListOffer:
    """What a stems list lets a reader do with a row, which is what its owner can answer for.

    The converter's gathered recordings and a reconstruction's recorded assignment are the same
    rows drawn the same way; what differs is the gestures each owner honors. A list states that
    here, once, so a drawing step reads one declaration rather than asking a flag of its own.
    """

    master_box: bool
    removal: bool
    keeps_last_row: bool
    dragging: bool


GATHERED_SOURCES: StemsListOffer = StemsListOffer(
    master_box=False,
    removal=True,
    keeps_last_row=False,
    dragging=True,
)

RECORDED_ASSIGNMENT: StemsListOffer = StemsListOffer(
    master_box=True,
    removal=True,
    keeps_last_row=True,
    dragging=False,
)
