from typing import Dict, Final, FrozenSet, List, NamedTuple, Sequence

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.parse.song import parse_planes
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.sizes import phrase_size
from sampletones_player.specification.compression import MAX_PHRASE_IDS

MIN_CANDIDATE_LENGTH: Final[int] = 3
MAX_CANDIDATE_LENGTH: Final[int] = 48
MAX_CANDIDATE_ENTRIES: Final[int] = 200_000
MAX_SEARCH_ROUNDS: Final[int] = 64
CONFIRMED_CANDIDATES: Final[int] = 3
SHIFTED_OCCURRENCE_TRANSPOSE: Final[int] = 1


class _Span(NamedTuple):
    start: int
    end: int


class _Occurrence(NamedTuple):
    plane: int
    position: int


class _Candidate(NamedTuple):
    gain: int
    body: bytes


def _residue_spans(parse: Parse) -> List[_Span]:
    spans: List[_Span] = []
    position = 0
    for token in parse.tokens:
        if isinstance(token, LiteralToken):
            spans.append(_Span(start=position, end=position + token.ticks))

        position += token.ticks

    return spans


def _candidates(
    indices: Sequence[PlaneIndex],
    parses: Sequence[Parse],
) -> Dict[bytes, List[_Occurrence]]:
    found: Dict[bytes, List[_Occurrence]] = {}
    entries = 0
    for plane, (index, parse) in enumerate(zip(indices, parses)):
        for span in _residue_spans(parse):
            if entries > MAX_CANDIDATE_ENTRIES:
                return found

            for position in range(span.start, span.end):
                longest = min(MAX_CANDIDATE_LENGTH, span.end - position)
                for length in range(MIN_CANDIDATE_LENGTH, longest + 1):
                    key = index.differences[position : position + length - 1]
                    found.setdefault(key, []).append(
                        _Occurrence(plane=plane, position=position),
                    )
                    entries += 1

    return found


def _spread(
    occurrences: Sequence[_Occurrence],
    length: int,
) -> List[_Occurrence]:
    spread: List[_Occurrence] = []
    reached = -1
    covered = -1
    for occurrence in occurrences:
        if occurrence.plane != covered or occurrence.position >= reached:
            spread.append(occurrence)
            covered = occurrence.plane
            reached = occurrence.position + length

    return spread


def _gain(
    occurrences: Sequence[_Occurrence],
    length: int,
    parses: Sequence[Parse],
    phrase_id: int,
) -> int:
    parsed = 0
    tokens = 0
    for order, occurrence in enumerate(occurrences):
        costs = parses[occurrence.plane].costs
        parsed += costs[occurrence.position + length] - costs[occurrence.position]
        tokens += phrase_size(phrase_id, 0 if order == 0 else SHIFTED_OCCURRENCE_TRANSPOSE)

    return parsed - tokens


def _ranked(
    indices: Sequence[PlaneIndex],
    parses: Sequence[Parse],
    phrase_id: int,
) -> List[_Candidate]:
    ranked: List[_Candidate] = []
    for key, occurrences in _candidates(indices, parses).items():
        length = len(key) + 1
        spread = _spread(occurrences, length)
        if len(spread) < 2:
            continue

        first = spread[0]
        body = indices[first.plane].plane[first.position : first.position + length]
        gain = _gain(spread, length, parses, phrase_id) - Phrase(body=body).size
        if gain > 0:
            ranked.append(_Candidate(gain=gain, body=body))

    ranked.sort(key=lambda candidate: (-candidate.gain, candidate.body))
    return ranked[:CONFIRMED_CANDIDATES]


def _total(table: PhraseTable, parses: Sequence[Parse]) -> int:
    return table.size + sum(parse.size for parse in parses)


def search_phrases(
    indices: Sequence[PlaneIndex],
    table: PhraseTable,
    options: CodecOptions,
    boundaries: FrozenSet[int],
) -> PhraseTable:
    """Fills the dictionary with the phrases the song's own planes repeat.

    A candidate is scored by what the parse pays for it today against what a token naming it
    would pay instead, the entry it takes in the dictionary included, so a run a hold already
    covers for one byte scores nothing and the slots go to shapes that repeat at a price. The
    best few candidates of each round are confirmed by parsing the whole song again with each
    one added, and the round keeps whichever genuinely shrank the song.

    Candidates are counted by their shape rather than their values, so a figure played at five
    pitches is one candidate seen five times.

    Args:
        indices: The planes and the readings of them matching is decided against.
        table: The phrases the instruments seeded.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on.

    Returns:
        PhraseTable: The seeded phrases alongside the ones the search earned.
    """
    parses = parse_planes(indices, table, options, boundaries)
    total = _total(table, parses)
    for _ in range(MAX_SEARCH_ROUNDS):
        if len(table) == MAX_PHRASE_IDS:
            return table

        settled = False
        for candidate in _ranked(indices, parses, len(table)):
            enlarged = phrase_table(table.phrases + (Phrase(body=candidate.body),))
            trial = parse_planes(
                indices,
                enlarged,
                options,
                boundaries,
            )
            if _total(enlarged, trial) < total:
                table = enlarged
                parses = trial
                total = _total(enlarged, trial)
                settled = True
                break

        if not settled:
            return table

    return table
