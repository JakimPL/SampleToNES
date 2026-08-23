from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class TrackerColors(BaseModel, extra="forbid", frozen=True):
    """The semantic text colours shared across every tracker view.

    One palette feeds the pattern grid, the order table, and the history detail so a
    concept keeps its colour everywhere. Three of the tokens read a voice slot: ``voice``
    is what the slot wears while it names nothing, and ``sample`` and ``instrument`` are
    the two kinds a named voice can be, so the slot's colour reports what it holds.
    ``transpose`` and ``volume`` carry the other two slots, and the ``frame`` and ``row``
    indices and the ``order`` entries carry the grids around them. Defining them once
    keeps every panel in step.
    """

    voice: WrittenColor
    transpose: WrittenColor
    volume: WrittenColor
    sample: WrittenColor
    instrument: WrittenColor
    frame: WrittenColor
    row: WrittenColor
    order: WrittenColor
