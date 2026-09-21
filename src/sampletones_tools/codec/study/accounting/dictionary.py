from typing import Final

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_tools.codec.study.accounting.finding import NOTHING, Finding
from sampletones_tools.codec.study.accounting.runs import runs

REPEATED: Final[int] = 2
MIN_RLE_RUN: Final[int] = 3
RLE_RUN_SIZE: Final[int] = 2


def plateaus(table: PhraseTable) -> Finding:
    """What run-length coding inside phrase bodies would spare on the plateaus they hold (H2).

    A phrase is stored verbatim, a value resting for several ticks spelled out once per tick.
    A run coded as its value and its count takes two bytes however long it rests.

    Args:
        table: The dictionary.

    Returns:
        Finding: The body bytes sitting in a repeat, and the bytes run-length coding would spare.
    """
    finding = NOTHING
    for phrase in table.phrases:
        for run in runs(phrase.body):
            if run >= REPEATED:
                finding += Finding(run - 1, max(0, run - RLE_RUN_SIZE) if run >= MIN_RLE_RUN else 0)

    return finding
