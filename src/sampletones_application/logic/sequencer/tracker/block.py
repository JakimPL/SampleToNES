from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

from sampletones_core.project.instruments.note_off import NoteOff

BlockNote = Union[str, NoteOff]
BlockKey = Tuple[int, int]


@dataclass(frozen=True)
class TrackerBlock:
    """A rectangle of tracker values, addressed by the offsets it was read at.

    A key is a row offset paired with a slot offset. The row offset counts down from the block's
    first row; the slot offset is measured from the base of the column the block begins in, so it
    stays a multiple of three apart from the column it is replayed against and each value keeps
    the kind of subcolumn it was read from.

    A cell reaches the block in one of three states, and the maps hold them apart: a key carrying
    a value writes that value, a key carrying ``None`` writes emptiness, and an absent key states
    that the block says nothing about that cell — which is how a sample column its channels
    disagree over stays transparent to whatever it is pasted onto.

    Notes, transposes and volumes are kept in maps of their own so the kind of a value is
    structural. It also fixes the order a write takes: every note lands before the transposes and
    volumes sharing its row, which matters where a sample-column note clears the channels around
    it.

    A note names a sample by id rather than by instrument, so it carries a pitch and leaves the
    channel to whichever column it is written into.
    """

    notes: Dict[BlockKey, Optional[BlockNote]]
    transposes: Dict[BlockKey, Optional[int]]
    volumes: Dict[BlockKey, Optional[int]]
