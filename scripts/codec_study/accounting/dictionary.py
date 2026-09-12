from collections import Counter
from typing import Dict, Final, Iterable

from codec_study.accounting.finding import NOTHING, Finding
from codec_study.accounting.runs import runs
from codec_study.accounting.tokens import ReadToken
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.specification.compression import PHRASE_COUNT_SIZE

REPEATED: Final[int] = 2
MIN_RLE_RUN: Final[int] = 3
RLE_RUN_SIZE: Final[int] = 2
DEFAULT_COUNT_SIZE: Final[int] = 1


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


def default_counts(
    table: PhraseTable,
    tokens: Iterable[ReadToken],
) -> Finding:
    """What a default count stored with each phrase would spare on the count bytes (H4).

    Every phrase token carries the ticks it plays for. A phrase played mostly for one length
    could state that length once in its body, and a token playing it that long could leave the
    count byte out.

    Args:
        table: The dictionary.
        tokens: Every token of every plane.

    Returns:
        Finding: The count bytes phrase tokens carry, and the bytes a default would spare.
    """
    counts: Dict[int, Counter[int]] = {phrase_id: Counter() for phrase_id in range(len(table))}
    for token in tokens:
        if token.phrase_id is not None:
            counts[token.phrase_id][token.ticks] += 1

    targeted = PHRASE_COUNT_SIZE * sum(sum(counter.values()) for counter in counts.values())
    saving = 0
    for counter in counts.values():
        if counter:
            (_, modal), *_ = counter.most_common(1)
            saving += max(0, PHRASE_COUNT_SIZE * modal - DEFAULT_COUNT_SIZE)

    return Finding(targeted, saving)
