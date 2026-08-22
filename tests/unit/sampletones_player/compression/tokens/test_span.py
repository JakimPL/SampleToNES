from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_player.compression.encode import emit
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.span import TokenSpan, token_span
from sampletones_player.compression.tokens.types import TokenUnion
from sampletones_player.specification.compression import (
    MAX_HOLD_TICKS,
    MAX_PHRASE_TICKS,
    PHRASE_ID_ESCAPE,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase

FIRST_TOKEN: Final[int] = 0
CHEAP_ID: Final[int] = 1
SHIFT: Final[int] = 5
PHRASE_PLAY_TICKS: Final[int] = 10


class TestWhatAWrittenTokenTakesAndCovers(BaseTestSuite):
    """A stream is walked by its opcodes alone, so each token states its own bytes and ticks."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: TokenSpan
        name: str
        token: TokenUnion

        @property
        def label(self) -> str:
            return self.name

    test_cases = (
        TestCase(name="hold", token=HoldToken(ticks=7), expected=TokenSpan(size=1, ticks=7)),
        TestCase(
            name="hold-longest",
            token=HoldToken(ticks=MAX_HOLD_TICKS),
            expected=TokenSpan(size=1, ticks=MAX_HOLD_TICKS),
        ),
        TestCase(
            name="literal",
            token=LiteralToken(values=b"\x01\x02\x03"),
            expected=TokenSpan(size=4, ticks=3),
        ),
        TestCase(
            name="phrase",
            token=PhraseToken(phrase_id=CHEAP_ID, ticks=PHRASE_PLAY_TICKS, transpose=0),
            expected=TokenSpan(size=2, ticks=PHRASE_PLAY_TICKS),
        ),
        TestCase(
            name="phrase-shifted",
            token=PhraseToken(phrase_id=CHEAP_ID, ticks=PHRASE_PLAY_TICKS, transpose=SHIFT),
            expected=TokenSpan(size=3, ticks=PHRASE_PLAY_TICKS),
        ),
        TestCase(
            name="phrase-escaped",
            token=PhraseToken(phrase_id=PHRASE_ID_ESCAPE, ticks=PHRASE_PLAY_TICKS, transpose=0),
            expected=TokenSpan(size=3, ticks=PHRASE_PLAY_TICKS),
        ),
        TestCase(
            name="phrase-escaped-shifted",
            token=PhraseToken(
                phrase_id=PHRASE_ID_ESCAPE,
                ticks=PHRASE_PLAY_TICKS,
                transpose=SHIFT,
            ),
            expected=TokenSpan(size=4, ticks=PHRASE_PLAY_TICKS),
        ),
        TestCase(
            name="phrase-longest",
            token=PhraseToken(phrase_id=CHEAP_ID, ticks=MAX_PHRASE_TICKS, transpose=0),
            expected=TokenSpan(size=2, ticks=MAX_PHRASE_TICKS),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_span_states_what_the_token_takes(self, test_case: TestCase) -> None:
        span = token_span(emit([test_case.token]), FIRST_TOKEN)
        assert span.size == test_case.expected.size

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_span_states_what_the_token_covers(self, test_case: TestCase) -> None:
        span = token_span(emit([test_case.token]), FIRST_TOKEN)
        assert span.ticks == test_case.expected.ticks

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_span_reaches_the_byte_the_next_token_begins_at(self, test_case: TestCase) -> None:
        stream = emit([test_case.token, HoldToken(ticks=1)])
        assert token_span(stream, FIRST_TOKEN).size == len(stream) - 1


class TestWalkingAStream:
    """The spans of a stream's tokens sum to the stream itself."""

    def test_the_sizes_reach_the_streams_last_byte(self) -> None:
        tokens = (
            LiteralToken(values=b"\x01\x02"),
            HoldToken(ticks=3),
            PhraseToken(phrase_id=CHEAP_ID, ticks=4, transpose=SHIFT),
        )
        stream = emit(tokens)
        position = 0
        for _ in tokens:
            position += token_span(stream, position).size

        assert position == len(stream)

    def test_the_ticks_reach_the_songs_length(self) -> None:
        tokens = (
            LiteralToken(values=b"\x01\x02"),
            HoldToken(ticks=3),
            PhraseToken(phrase_id=CHEAP_ID, ticks=4, transpose=0),
        )
        stream = emit(tokens)
        position = 0
        covered = 0
        for _ in tokens:
            span = token_span(stream, position)
            covered += span.ticks
            position += span.size

        assert covered == 2 + 3 + 4
