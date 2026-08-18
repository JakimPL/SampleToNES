from pydantic import BaseModel

from sampletones_application.utils.palette.colors.written import WrittenColor


class TrackerColors(BaseModel, extra="forbid", frozen=True):
    """The semantic text colours shared across every tracker view.

    One palette feeds the pattern grid, the order table, and the history detail so a
    concept keeps its colour everywhere: ``instrument`` (the note/sample reference,
    yellow like ``sample``), ``transpose``, ``volume``, ``sample``, the ``frame`` and
    ``row`` indices, and the ``order`` entries. Defining them once keeps every panel in
    step.
    """

    instrument: WrittenColor
    transpose: WrittenColor
    volume: WrittenColor
    sample: WrittenColor
    frame: WrittenColor
    row: WrittenColor
    order: WrittenColor
