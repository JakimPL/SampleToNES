from time import process_time
from typing import Final, Sequence, Tuple

from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_tools.codec.study.measure import Encoding
from sampletones_tools.codec.study.sandbox.defaults import modal_counts, no_defaults
from sampletones_tools.codec.study.sandbox.grammar import Grammar
from sampletones_tools.codec.study.sandbox.parse import StudyParse
from sampletones_tools.codec.study.sandbox.reference import Reference
from sampletones_tools.codec.study.sandbox.verify import plays_back

DEFAULT_ROUNDS: Final[int] = 3


def encode_grammar(
    reference: Reference,
    grammar: Grammar,
) -> Encoding:
    """Prices a song under a grammar, over the dictionary the production codec settled on.

    Args:
        reference: The song, its dictionary and its matches.
        grammar: The grammar.

    Returns:
        Encoding: The bytes each stream would take, timed, and whether the tokens play back.
    """
    started = process_time()
    parses = _parses(reference, grammar)
    seconds = process_time() - started
    return Encoding(
        header=SONG_HEADER_SIZE,
        phrases=len(reference.table),
        dictionary=grammar.costs.dictionary(reference.table),
        streams=tuple(parse.size for parse in parses),
        seconds=seconds,
        lossless=plays_back(parses, reference.table, reference.planes),
        written=None,
    )


def _parse_all(
    reference: Reference,
    grammar: Grammar,
    defaults: Sequence[int],
) -> Tuple[StudyParse, ...]:
    return reference.parses(grammar, defaults)


def _streams(parses: Sequence[StudyParse]) -> int:
    return sum(parse.size for parse in parses)


def _parses(
    reference: Reference,
    grammar: Grammar,
) -> Tuple[StudyParse, ...]:
    """Every plane under the grammar, its default counts settled where it carries them.

    A default count is read off the parse it serves, so the first reading takes the counts the
    baseline parse plays each phrase at, and each further round reads them off the parse that
    used them, stopping where they stand still or stop paying.
    """
    phrases = len(reference.table)
    if not grammar.default_counts:
        return _parse_all(reference, grammar, no_defaults(phrases))

    defaults = modal_counts(reference.baseline, phrases)
    parses = _parse_all(reference, grammar, defaults)
    for _ in range(DEFAULT_ROUNDS - 1):
        refined = modal_counts(parses, phrases)
        if refined == defaults:
            break

        trial = _parse_all(reference, grammar, refined)
        if _streams(trial) >= _streams(parses):
            break

        defaults = refined
        parses = trial

    return parses
