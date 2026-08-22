from typing import List, Mapping, NamedTuple

from sampletones_player.compression.dictionary.table import PhraseTable


class _KeptPhrase(NamedTuple):
    references: int
    phrase_id: int


def _pays_for_itself(
    table: PhraseTable,
    references: Mapping[int, int],
    savings: Mapping[int, int],
) -> List[_KeptPhrase]:
    return [
        _KeptPhrase(references=references[phrase_id], phrase_id=phrase_id)
        for phrase_id in range(len(table))
        if references[phrase_id] > 0 and savings[phrase_id] > table[phrase_id].size
    ]


def prune(
    table: PhraseTable,
    references: Mapping[int, int],
    savings: Mapping[int, int],
) -> PhraseTable:
    """Rebuilds a table around the phrases that pay for themselves, most named first.

    A phrase earns its place by sparing the streams more bytes than its own entry takes, and the
    ids it competes for are worth a byte apiece: the cheap ones ride inside an opcode, so the
    phrases named most often take them and the tokens naming those shed a byte each.

    Args:
        table: The table the tokens were parsed against.
        references: How many tokens name each phrase id.
        savings: The bytes each phrase's tokens spare the streams.

    Returns:
        PhraseTable: The phrases worth keeping, ordered by how often they are named.
    """
    kept = _pays_for_itself(table, references, savings)
    kept.sort(key=lambda entry: (-entry.references, entry.phrase_id))
    return PhraseTable(phrases=tuple(table[entry.phrase_id] for entry in kept))
