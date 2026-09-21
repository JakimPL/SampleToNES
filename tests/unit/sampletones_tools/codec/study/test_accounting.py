from dataclasses import dataclass
from typing import Dict, Final, Sequence, Tuple

import pytest

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.compression.encode import emit
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.types import TokenUnion
from sampletones_player.specification.compression import MAX_HOLD_TICKS, TokenTag
from sampletones_player.specification.planes import PLANES, PlaneRole
from sampletones_tools.codec.study.accounting.coincident import coincident_starts
from sampletones_tools.codec.study.accounting.dictionary import plateaus
from sampletones_tools.codec.study.accounting.finding import Finding
from sampletones_tools.codec.study.accounting.pairs import ramps_in_literals, set_holds
from sampletones_tools.codec.study.accounting.runs import ramps, runs
from sampletones_tools.codec.study.accounting.shares import hold_chains
from sampletones_tools.codec.study.accounting.tokens import ReadToken, read_tokens
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ESCAPED_PHRASE_ID: Final[int] = 70
REST: Final[int] = 32


class TestReadTokensReadsBackWhatEmitWrote:
    """Every token comes back with its tag, where it starts, what it takes and what it carries."""

    tokens: Final[Tuple[TokenUnion, ...]] = (
        HoldToken(ticks=3),
        LiteralToken(values=b"\x01\x02"),
        PhraseToken(phrase_id=2, ticks=4, transpose=0, default=False),
        PhraseToken(phrase_id=ESCAPED_PHRASE_ID, ticks=2, transpose=3, default=False),
    )

    def test_the_tokens_come_back_in_order(self) -> None:
        read = read_tokens(emit(self.tokens), DICTIONARY)

        assert [token.tag for token in read] == [
            TokenTag.HOLD,
            TokenTag.LITERAL,
            TokenTag.PHRASE,
            TokenTag.TRANSPOSED_PHRASE,
        ]
        assert [token.tick for token in read] == [0, 3, 5, 9]
        assert [token.ticks for token in read] == [3, 2, 4, 2]
        assert [token.size for token in read] == [token.size for token in self.tokens]

    def test_the_operands_come_back(self) -> None:
        read = read_tokens(emit(self.tokens), DICTIONARY)

        assert [token.payload for token in read] == [b"", b"\x01\x02", b"", b""]
        assert [token.phrase_id for token in read] == [None, None, 2, ESCAPED_PHRASE_ID]
        assert [token.transpose for token in read] == [0, 0, 0, 3]


class TestRuns(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        data: bytes
        expected: Tuple[int, ...]

    test_cases = (
        TestCase(label="empty", data=b"", expected=()),
        TestCase(label="one value", data=b"\x07", expected=(1,)),
        TestCase(label="two plateaus", data=b"\x01\x01\x01\x02\x02", expected=(3, 2)),
        TestCase(label="no repeat", data=b"\x01\x02\x03", expected=(1, 1, 1)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_run_lengths_cover_the_data(self, test_case: TestCase) -> None:
        assert runs(test_case.data) == test_case.expected
        assert sum(test_case.expected) == len(test_case.data)


class TestRamps(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        data: bytes
        expected: Tuple[int, ...]

    test_cases = (
        TestCase(label="a rise", data=b"\x01\x02\x03\x04\x05", expected=(5,)),
        TestCase(label="a plateau steps nowhere", data=b"\x05\x05\x05", expected=()),
        TestCase(label="a rise across the byte wraps", data=b"\xfe\xff\x00\x01", expected=(4,)),
        TestCase(label="two steps of different size", data=b"\x01\x02\x04", expected=(2, 2)),
        TestCase(label="a fall after a rest", data=b"\x09\x09\x08\x07", expected=(3,)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_constant_step_runs_are_found(self, test_case: TestCase) -> None:
        assert ramps(test_case.data) == test_case.expected


DICTIONARY: Final[PhraseTable] = phrase_table(tuple(Phrase(body=bytes((value,))) for value in range(4)))


class TestHoldChains(BaseTestSuite):
    """A wide hold pays two bytes for up to sixty-four full holds, and one for the ticks left."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        holds: Tuple[int, ...]
        expected: Finding

    test_cases = (
        TestCase(label="one hold is no chain", holds=(MAX_HOLD_TICKS,), expected=Finding(0, 0)),
        TestCase(label="a full hold and a rest break even", holds=(MAX_HOLD_TICKS, REST), expected=Finding(2, 0)),
        TestCase(
            label="three full holds and a rest spare one",
            holds=(MAX_HOLD_TICKS, MAX_HOLD_TICKS, MAX_HOLD_TICKS, REST),
            expected=Finding(4, 1),
        ),
        TestCase(
            label="sixty-four full holds become one wide hold",
            holds=(MAX_HOLD_TICKS,) * MAX_HOLD_TICKS,
            expected=Finding(MAX_HOLD_TICKS, MAX_HOLD_TICKS - 2),
        ),
        TestCase(
            label="sixty-five full holds need two wide holds",
            holds=(MAX_HOLD_TICKS,) * (MAX_HOLD_TICKS + 1),
            expected=Finding(MAX_HOLD_TICKS + 1, MAX_HOLD_TICKS + 1 - 4),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_chain_is_priced_against_wide_holds(self, test_case: TestCase) -> None:
        stream = emit([HoldToken(ticks=ticks) for ticks in test_case.holds])

        assert hold_chains(read_tokens(stream, DICTIONARY)) == test_case.expected

    def test_a_literal_breaks_the_chain(self) -> None:
        stream = emit(
            [
                HoldToken(ticks=MAX_HOLD_TICKS),
                LiteralToken(values=b"\x01"),
                HoldToken(ticks=MAX_HOLD_TICKS),
                HoldToken(ticks=MAX_HOLD_TICKS),
            ]
        )

        assert hold_chains(read_tokens(stream, DICTIONARY)) == Finding(2, 0)


class TestSetHolds(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tokens: Tuple[TokenUnion, ...]
        expected: Finding

    test_cases = (
        TestCase(
            label="a value then a rest is a pair",
            tokens=(LiteralToken(values=b"\x05"), HoldToken(ticks=10)),
            expected=Finding(3, 1),
        ),
        TestCase(
            label="two values then a rest is no pair",
            tokens=(LiteralToken(values=b"\x05\x06"), HoldToken(ticks=10)),
            expected=Finding(0, 0),
        ),
        TestCase(
            label="a rest then a value is no pair",
            tokens=(HoldToken(ticks=10), LiteralToken(values=b"\x05")),
            expected=Finding(0, 0),
        ),
        TestCase(
            label="every pair counts",
            tokens=(
                LiteralToken(values=b"\x05"),
                HoldToken(ticks=10),
                LiteralToken(values=b"\x06"),
                HoldToken(ticks=10),
            ),
            expected=Finding(6, 2),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pairs_are_priced_at_two_bytes(self, test_case: TestCase) -> None:
        assert set_holds(read_tokens(emit(list(test_case.tokens)), DICTIONARY)) == test_case.expected


class TestRampsInLiterals(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        values: bytes
        expected: Finding

    test_cases = (
        TestCase(label="a rise of five", values=b"\x01\x02\x03\x04\x05", expected=Finding(5, 2)),
        TestCase(label="a rise of three breaks even", values=b"\x01\x02\x03", expected=Finding(3, 0)),
        TestCase(label="a rise of two is no ramp", values=b"\x01\x02", expected=Finding(0, 0)),
        TestCase(label="a plateau is no ramp", values=b"\x05\x05\x05\x05", expected=Finding(0, 0)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_ramps_are_priced_at_three_bytes(self, test_case: TestCase) -> None:
        assert (
            ramps_in_literals(read_tokens(emit([LiteralToken(values=test_case.values)]), DICTIONARY))
            == test_case.expected
        )

    def test_a_ramp_inside_a_hold_is_none(self) -> None:
        assert ramps_in_literals(read_tokens(emit([HoldToken(ticks=5)]), DICTIONARY)) == Finding(0, 0)


def _starting_at(ticks: Sequence[int]) -> Tuple[ReadToken, ...]:
    return tuple(
        ReadToken(
            tag=TokenTag.HOLD,
            tick=tick,
            size=1,
            ticks=1,
            payload=b"",
            phrase_id=None,
            transpose=0,
        )
        for tick in ticks
    )


class TestCoincidentStarts:
    """Every channel carrying a timbre shares its first tick, and pulse one shares a second."""

    def test_a_channel_counts_the_ticks_both_its_planes_start_a_token_on(self) -> None:
        tokens: Dict[str, Tuple[ReadToken, ...]] = {name: _starting_at((0,)) for name in PlaneOrder.names()}
        tokens["pulse1_control"] = _starting_at((0, 5))
        tokens["pulse1_value"] = _starting_at((0, 5, 9))
        tokens["noise_value"] = _starting_at((0, 7))
        timbred = sum(1 for plane in PLANES if plane.role is PlaneRole.CONTROL)
        shared = timbred + 1

        assert coincident_starts(tokens) == Finding(2 * shared, shared)


class TestPlateausInBodies:
    def test_the_repeats_beyond_a_runs_first_byte_are_targeted(self) -> None:
        table = phrase_table((Phrase(body=b"\x01\x01\x01\x02\x02"), Phrase(body=b"\x03\x04")))

        assert plateaus(table) == Finding(3, 1)
