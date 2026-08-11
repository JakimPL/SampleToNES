from dataclasses import dataclass
from typing import Dict, Optional, Tuple

BlockKey = Tuple[int, int]


@dataclass(frozen=True)
class OrderBlock:
    """A rectangle of the order table, addressed by the offsets it was read at.

    A key is a row offset paired with a position offset, both counted from the cell the block
    begins at, so a block carries its own shape and lands wherever it is anchored.

    A cell reaches the block in one of three states, and the map holds them apart: a key carrying
    an index plays that pattern, a key carrying ``None`` silences the slot, and an absent key
    states that the block says nothing about that cell — which is how a master row its channels
    disagree over stays transparent to whatever it is pasted onto.

    Absence also settles how far a paste grows the order: a column the block says nothing about
    reaches nothing, so the order ends where the last written column does.
    """

    row_count: int
    position_count: int
    entries: Dict[BlockKey, Optional[int]]
