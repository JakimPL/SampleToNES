from typing import Final

import pytest

from sampletones_player.compression.encode import emit
from sampletones_player.compression.entries import stream_entry
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken

FIRST_TICK: Final[int] = 0
PHRASE_ID: Final[int] = 2
SHIFT: Final[int] = 7


class TestWhereAStreamIsReEntered:
    """A song coming round resumes at a byte, and the walk over the tokens finds it."""

    def test_the_first_tick_is_the_streams_own_first_byte(self) -> None:
        stream = emit([LiteralToken(values=b"\x01\x02"), HoldToken(ticks=3)])
        assert stream_entry(stream, FIRST_TICK) == 0

    def test_a_tick_a_token_starts_answers_with_that_tokens_byte(self) -> None:
        literal = LiteralToken(values=b"\x01\x02")
        stream = emit([literal, HoldToken(ticks=3), PhraseToken(phrase_id=PHRASE_ID, ticks=4, transpose=0)])
        assert stream_entry(stream, literal.ticks) == literal.size

    def test_a_tick_further_in_walks_past_every_token_before_it(self) -> None:
        tokens = [
            LiteralToken(values=b"\x01\x02"),
            HoldToken(ticks=3),
            PhraseToken(phrase_id=PHRASE_ID, ticks=4, transpose=SHIFT),
        ]
        stream = emit(tokens)
        covered = sum(token.ticks for token in tokens[:2])
        assert stream_entry(stream, covered) == sum(token.size for token in tokens[:2])

    def test_a_tick_a_token_spans_is_refused(self) -> None:
        """A stream re-entered mid-token would leave the driver reading operands as opcodes."""
        stream = emit([HoldToken(ticks=8)])
        with pytest.raises(ValueError, match="spans tick"):
            stream_entry(stream, 3)
