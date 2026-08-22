from dataclasses import dataclass

import pytest

from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.sizes import phrase_size
from sampletones_player.specification.compression import (
    CHEAP_PHRASE_IDS,
    MAX_BYTE_VALUE,
    OPCODE_SIZE,
    PHRASE_COUNT_SIZE,
    PHRASE_ESCAPE_SIZE,
    TRANSPOSE_SIZE,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestWhatAPhraseTokenCosts(BaseTestSuite):
    """A token's bytes are what the parse is decided in, so each states its own size."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        phrase_id: int
        transpose: int

        @property
        def label(self) -> str:
            shift = "shifted" if self.transpose else "plain"
            return f"phrase_{self.phrase_id}_{shift}"

    test_cases = (
        TestCase(phrase_id=0, transpose=0, expected=OPCODE_SIZE + PHRASE_COUNT_SIZE),
        TestCase(
            phrase_id=0,
            transpose=1,
            expected=OPCODE_SIZE + PHRASE_COUNT_SIZE + TRANSPOSE_SIZE,
        ),
        TestCase(
            phrase_id=CHEAP_PHRASE_IDS,
            transpose=0,
            expected=OPCODE_SIZE + PHRASE_COUNT_SIZE + PHRASE_ESCAPE_SIZE,
        ),
        TestCase(
            phrase_id=CHEAP_PHRASE_IDS,
            transpose=MAX_BYTE_VALUE,
            expected=OPCODE_SIZE + PHRASE_COUNT_SIZE + PHRASE_ESCAPE_SIZE + TRANSPOSE_SIZE,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_phrase_token_pays_for_the_id_and_the_shift_it_names(self, test_case: TestCase) -> None:
        token = PhraseToken(phrase_id=test_case.phrase_id, ticks=1, transpose=test_case.transpose)
        assert token.size == test_case.expected == phrase_size(test_case.phrase_id, test_case.transpose)
