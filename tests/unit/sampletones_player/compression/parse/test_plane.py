from typing import Final, FrozenSet, Tuple

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.plane import parse_plane
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.types import TokenUnion
from sampletones_player.specification.compression import MAX_HOLD_TICKS, MAX_LITERAL_BYTES

EVERY_LAYER: Final[CodecOptions] = CodecOptions(
    holds=True,
    phrases=True,
    transposition=True,
    search=False,
)
LITERALS_ONLY: Final[CodecOptions] = CodecOptions(
    holds=False,
    phrases=False,
    transposition=False,
    search=False,
)
START: Final[FrozenSet[int]] = frozenset({0})
MOTIF: Final[bytes] = bytes((40, 44, 47, 44))


def parsed(
    plane: bytes,
    phrases: Tuple[Phrase, ...] = (),
    options: CodecOptions = EVERY_LAYER,
    boundaries: FrozenSet[int] = START,
) -> Parse:
    return parse_plane(
        PlaneIndex.from_plane(plane),
        PhraseMatcher(phrase_table(phrases)),
        options,
        boundaries,
    )


def starts(parse: Parse) -> Tuple[int, ...]:
    positions = []
    position = 0
    for token in parse.tokens:
        positions.append(position)
        position += token.ticks

    return tuple(positions)


class TestTheParseCoversThePlaneCheaply:
    """Every way of covering a tick is an edge, and the encoding is the cheapest path across them."""

    def test_the_tokens_cover_every_tick_of_the_plane(self) -> None:
        plane = bytes((1, 1, 1, 2, 3, 3))
        parse = parsed(plane)
        assert sum(token.ticks for token in parse.tokens) == len(plane)

    def test_the_cost_of_the_whole_plane_is_the_cost_of_its_tokens(self) -> None:
        parse = parsed(bytes((1, 1, 2, 2, 2, 9)))
        assert parse.size == sum(token.size for token in parse.tokens)

    def test_a_run_reaches_the_stream_as_a_hold(self) -> None:
        parse = parsed(bytes((7,)) * 40)
        assert parse.tokens == (LiteralToken(values=bytes((7,))), HoldToken(ticks=39))

    def test_a_run_longer_than_one_hold_reaches_the_stream_as_several(self) -> None:
        parse = parsed(bytes((7,)) * (2 * MAX_HOLD_TICKS + 1))
        assert parse.tokens[1:] == (HoldToken(ticks=MAX_HOLD_TICKS),) * 2

    def test_a_plane_the_codec_finds_nothing_in_spells_itself_out(self) -> None:
        plane = bytes(range(MAX_LITERAL_BYTES + 4))
        parse = parsed(plane, options=LITERALS_ONLY)
        assert parse.tokens == (
            LiteralToken(values=plane[:MAX_LITERAL_BYTES]),
            LiteralToken(values=plane[MAX_LITERAL_BYTES:]),
        )

    def test_a_figure_the_dictionary_holds_reaches_the_stream_as_a_phrase(self) -> None:
        parse = parsed(MOTIF, (Phrase(body=MOTIF),))
        assert parse.tokens == (PhraseToken(phrase_id=0, ticks=len(MOTIF), transpose=0),)

    def test_the_same_figure_played_higher_names_the_same_phrase(self) -> None:
        higher = bytes(value + 7 for value in MOTIF)
        parse = parsed(higher, (Phrase(body=MOTIF),))
        assert parse.tokens == (PhraseToken(phrase_id=0, ticks=len(MOTIF), transpose=7),)

    def test_a_phrase_the_layer_switches_off_is_spelled_out_instead(self) -> None:
        parse = parsed(MOTIF, (Phrase(body=MOTIF),), options=LITERALS_ONLY)
        assert parse.tokens == (LiteralToken(values=MOTIF),)


class TestABoundaryIsATickATokenStartsOn:
    """A loop entry is re-entered mid-stream, so a token starts there and leans on nothing before it."""

    def test_a_token_starts_on_every_boundary(self) -> None:
        plane = bytes((3,)) * 20
        parse = parsed(plane, boundaries=frozenset({0, 7, 13}))
        assert {0, 7, 13} <= set(starts(parse))

    def test_a_boundary_is_reached_by_a_token_stating_its_own_value(self) -> None:
        """A hold plays the value the plane already reached, which a re-entry has yet to state."""
        plane = bytes((3,)) * 20
        parse = parsed(plane, boundaries=frozenset({0, 7}))
        entered = parse.tokens[starts(parse).index(7)]
        assert isinstance(entered, LiteralToken)

    def test_the_plane_still_reads_back_the_same_ticks(self) -> None:
        plane = bytes((3,)) * 9 + bytes((4,)) * 9
        bounded: Tuple[TokenUnion, ...] = parsed(plane, boundaries=frozenset({0, 5, 12})).tokens
        assert sum(token.ticks for token in bounded) == len(plane)
