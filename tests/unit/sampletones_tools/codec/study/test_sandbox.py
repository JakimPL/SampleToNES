from dataclasses import dataclass, replace
from pathlib import Path
from random import Random
from typing import Final, FrozenSet, List, Sequence, Tuple

import pytest

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.compression.encode import STREAM_START
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.parse.boundaries import Boundaries
from sampletones_player.compression.parse.plane import parse_plane as parse_production
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.specification.compression import (
    CHEAP_PHRASE_IDS,
    MAX_HOLD_TICKS,
)
from sampletones_player.specification.planes import PLANE_COUNT, PLANES, PlaneRole
from sampletones_shared.music import Tuning
from sampletones_tools.codec.study.corpus.song import SongGroup, StudySong
from sampletones_tools.codec.study.sandbox.context import PlaneContext
from sampletones_tools.codec.study.sandbox.costs import PRODUCTION_COSTS, SET_HOLD_BOUND, Costs
from sampletones_tools.codec.study.sandbox.decode import play_tokens
from sampletones_tools.codec.study.sandbox.defaults import modal_counts, no_defaults
from sampletones_tools.codec.study.sandbox.edges.generator import offered_lengths
from sampletones_tools.codec.study.sandbox.encode import encode_grammar
from sampletones_tools.codec.study.sandbox.grammar import BASELINE_GRAMMAR, Grammar
from sampletones_tools.codec.study.sandbox.parse import StudyParse, parse_plane
from sampletones_tools.codec.study.sandbox.reference import reference
from sampletones_tools.codec.study.sandbox.tokens import Hold, Literal, Play, SetHold, StudyToken, WideHold
from sampletones_tools.codec.study.sandbox.verify import verify_baseline
from sampletones_tools.codec.study.variants.production import compress_baseline
from sampletones_tools.codec.study.variants.sandbox import DEFAULT_COUNT_COSTS, GRAMMAR_VARIANTS, GrammarVariant
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.player import playable
from tests.suite.study import NO_STUDY_SLICES, lowest_notes

ENTRIES: Final[FrozenSet[int]] = frozenset({STREAM_START})
FIGURES: Final[Tuple[bytes, ...]] = (b"\x0a\x0c\x0f\x0f\x0f\x0f\x0f\x0f", b"\x03\x04\x05\x06")
TABLE: Final[PhraseTable] = phrase_table(Phrase(body=body) for body in FIGURES)
NO_TABLE: Final[PhraseTable] = phrase_table(())
SONG_TICKS: Final[int] = 200
SEED: Final[int] = 20260912
WIDE_HOLD: Final[Grammar] = replace(BASELINE_GRAMMAR, wide_hold=True)
START_HOLD: Final[Grammar] = replace(BASELINE_GRAMMAR, start_hold=True)
EVERY_HOLD: Final[Grammar] = replace(BASELINE_GRAMMAR, every_length=True)
SET_HOLD_ESCAPE: Final[Grammar] = replace(BASELINE_GRAMMAR, set_hold=True)
SET_HOLD_REALLOCATED: Final[Grammar] = replace(
    BASELINE_GRAMMAR, set_hold=True, costs=replace(PRODUCTION_COSTS, set_hold=SET_HOLD_BOUND)
)
DEFAULT_COUNTS: Final[Grammar] = replace(BASELINE_GRAMMAR, default_counts=True, costs=DEFAULT_COUNT_COSTS)


def _figures_plane(random: Random, ticks: int) -> bytes:
    values = bytearray()
    while len(values) < ticks:
        figure = random.choice(FIGURES)
        shift = random.randrange(20)
        values.extend((value + shift) % 256 for value in figure)
        values.extend([values[-1]] * random.randrange(7))

    return bytes(values[:ticks])


def _runs_plane(random: Random, ticks: int) -> bytes:
    values = bytearray()
    while len(values) < ticks:
        values.extend([random.randrange(16)] * random.randint(1, 40))

    return bytes(values[:ticks])


def _dense_plane(random: Random, ticks: int) -> bytes:
    return bytes(random.randrange(50) for _ in range(ticks))


def _song(ticks: int) -> StudySong:
    random = Random(SEED)
    planes: List[bytes] = []
    for plane in PLANES:
        if plane.spans_flagged_ticks:
            planes.append(b"")
        elif plane.role is PlaneRole.CONTROL:
            planes.append(playable(plane, _runs_plane(random, ticks)))
        else:
            planes.append(playable(plane, _figures_plane(random, ticks)))

    return StudySong(
        name="song",
        group=SongGroup.PROJECT,
        source=Path("song.stp"),
        planes=SongPlanes(planes=PlaneOrder.across(planes)),
        seeds=tuple(Phrase(body=body) for body in FIGURES),
        pitches=PitchTable.from_tuning(Tuning()),
        notes=lowest_notes(ticks),
        slices=NO_STUDY_SLICES,
    )


def _context(
    plane: bytes,
    table: PhraseTable,
    costs: Costs,
    defaults: Sequence[int],
) -> PlaneContext:
    cache = MatchCache([PlaneIndex.from_plane(plane)])
    return PlaneContext(
        index=cache.index(0),
        matcher=PhraseMatcher(table, 0, cache),
        boundaries=Boundaries.across(len(plane), ENTRIES),
        transposition=EVERY_LAYER.transposition,
        defaults=tuple(defaults),
        costs=costs,
    )


def _parse(
    plane: bytes,
    table: PhraseTable,
    grammar: Grammar,
    defaults: Sequence[int],
) -> StudyParse:
    return parse_plane(_context(plane, table, grammar.costs, defaults), grammar)


def _production_size(plane: bytes, table: PhraseTable) -> int:
    cache = MatchCache([PlaneIndex.from_plane(plane)])
    return parse_production(PhraseMatcher(table, 0, cache), EVERY_LAYER, ENTRIES).size


class TestTheBaselineGrammarReadsAsTheCodec(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        plane: bytes

    test_cases = (
        TestCase(label="an idle plane", plane=bytes(SONG_TICKS)),
        TestCase(label="a ramp", plane=bytes(range(SONG_TICKS))),
        TestCase(label="two runs", plane=bytes([5] * 10 + [7] * 10)),
        TestCase(label="figures at several pitches", plane=_figures_plane(Random(SEED), SONG_TICKS)),
        TestCase(label="runs of many lengths", plane=_runs_plane(Random(SEED), SONG_TICKS)),
        TestCase(label="dense values", plane=_dense_plane(Random(SEED), SONG_TICKS)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_plane_costs_what_the_production_parser_charges(self, test_case: TestCase) -> None:
        parse = _parse(test_case.plane, TABLE, BASELINE_GRAMMAR, no_defaults(len(TABLE)))

        assert parse.size == _production_size(test_case.plane, TABLE)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tokens_play_back(self, test_case: TestCase) -> None:
        parse = _parse(test_case.plane, TABLE, BASELINE_GRAMMAR, no_defaults(len(TABLE)))

        assert play_tokens(parse.tokens, TABLE, len(test_case.plane)) == test_case.plane


class TestPlayTokens(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        tokens: Tuple[StudyToken, ...]
        expected: bytes

    test_cases = (
        TestCase(
            label="a hold keeps the value a literal reached",
            tokens=(Literal(values=b"\x07"), Hold(ticks=3)),
            expected=b"\x07\x07\x07\x07",
        ),
        TestCase(
            label="a hold opening the stream keeps the seeded value",
            tokens=(Hold(ticks=2),),
            expected=b"\x00\x00",
        ),
        TestCase(
            label="a wide hold counts blocks of the longest plain hold",
            tokens=(Literal(values=b"\x09"), WideHold(blocks=2)),
            expected=b"\x09" * (1 + 2 * MAX_HOLD_TICKS),
        ),
        TestCase(
            label="a set-hold takes its value and keeps it",
            tokens=(SetHold(value=5, ticks=3), Hold(ticks=1)),
            expected=b"\x05\x05\x05\x05",
        ),
        TestCase(
            label="a phrase played past its end holds its final value",
            tokens=(Play(phrase_id=1, ticks=6, transpose=0, default=False),),
            expected=b"\x03\x04\x05\x06\x06\x06",
        ),
        TestCase(
            label="a shifted phrase plays every value shifted",
            tokens=(Play(phrase_id=1, ticks=2, transpose=10, default=True),),
            expected=b"\x0d\x0e",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_values_are_played(self, test_case: TestCase) -> None:
        assert play_tokens(test_case.tokens, TABLE, len(test_case.expected)) == test_case.expected

    def test_the_song_end_cuts_the_final_token(self) -> None:
        assert play_tokens((Literal(values=b"\x01"), Hold(ticks=5)), NO_TABLE, 3) == b"\x01\x01\x01"


class TestGrammarsPriceAPlane(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        plane: bytes
        table: PhraseTable
        grammar: Grammar
        defaults: Tuple[int, ...]
        expected: int

    idle = bytes(SONG_TICKS)
    two_runs = bytes([5] * 10 + [7] * 10)
    run_then_figure = bytes([5] * 6 + [9] * 5)
    figure_table = phrase_table((Phrase(body=b"\x05\x05\x09"),))
    repeated = bytes(b"\x01\x02\x03\x03" * 3)
    repeated_table = phrase_table((Phrase(body=b"\x01\x02\x03"),))
    test_cases = (
        TestCase(
            label="an idle plane pays a literal and a hold per block",
            plane=idle,
            table=NO_TABLE,
            grammar=BASELINE_GRAMMAR,
            defaults=(),
            expected=6,
        ),
        TestCase(
            label="a hold may open the stream over the seeded value",
            plane=idle,
            table=NO_TABLE,
            grammar=START_HOLD,
            defaults=(),
            expected=4,
        ),
        TestCase(
            label="a wide hold covers the full blocks at once",
            plane=idle,
            table=NO_TABLE,
            grammar=WIDE_HOLD,
            defaults=(),
            expected=5,
        ),
        TestCase(
            label="a wide hold opening the stream costs two bytes and a remainder",
            plane=idle,
            table=NO_TABLE,
            grammar=replace(WIDE_HOLD, start_hold=True),
            defaults=(),
            expected=3,
        ),
        TestCase(
            label="two runs pay a literal and a hold each",
            plane=two_runs,
            table=NO_TABLE,
            grammar=BASELINE_GRAMMAR,
            defaults=(),
            expected=6,
        ),
        TestCase(
            label="a three-byte set-hold breaks even with a literal and a hold",
            plane=two_runs,
            table=NO_TABLE,
            grammar=SET_HOLD_ESCAPE,
            defaults=(),
            expected=6,
        ),
        TestCase(
            label="a two-byte set-hold spares the hold",
            plane=two_runs,
            table=NO_TABLE,
            grammar=SET_HOLD_REALLOCATED,
            defaults=(),
            expected=4,
        ),
        TestCase(
            label="the longest hold alone overshoots where a figure begins",
            plane=run_then_figure,
            table=figure_table,
            grammar=BASELINE_GRAMMAR,
            defaults=(0,),
            expected=6,
        ),
        TestCase(
            label="a shorter hold lets the figure start where it matches",
            plane=run_then_figure,
            table=figure_table,
            grammar=EVERY_HOLD,
            defaults=(0,),
            expected=5,
        ),
        TestCase(
            label="a phrase played at its default count carries no count",
            plane=repeated,
            table=repeated_table,
            grammar=DEFAULT_COUNTS,
            defaults=(4,),
            expected=3,
        ),
        TestCase(
            label="a phrase played at another count carries it",
            plane=repeated,
            table=repeated_table,
            grammar=DEFAULT_COUNTS,
            defaults=(3,),
            expected=6,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_plane_costs_what_the_grammar_charges(self, test_case: TestCase) -> None:
        parse = _parse(test_case.plane, test_case.table, test_case.grammar, test_case.defaults)

        assert parse.size == test_case.expected
        assert play_tokens(parse.tokens, test_case.table, len(test_case.plane)) == test_case.plane


class TestCosts:
    def test_a_phrase_beyond_the_cheap_ids_pays_the_escape(self) -> None:
        assert PRODUCTION_COSTS.phrase(CHEAP_PHRASE_IDS - 1, 0, default=False) == 2
        assert PRODUCTION_COSTS.phrase(CHEAP_PHRASE_IDS, 0, default=False) == 3
        assert PRODUCTION_COSTS.phrase(0, 3, default=False) == 3

    def test_default_counts_halve_the_cheap_ids_and_widen_the_entries(self) -> None:
        assert DEFAULT_COUNT_COSTS.phrase(30, 0, default=True) == 1
        assert DEFAULT_COUNT_COSTS.phrase(31, 0, default=True) == 2
        assert DEFAULT_COUNT_COSTS.dictionary(TABLE) == TABLE.size + len(TABLE)

    def test_offered_lengths_are_the_longest_alone_or_every_one(self) -> None:
        assert tuple(offered_lengths(5, least=2, every=False)) == (5,)
        assert tuple(offered_lengths(5, least=2, every=True)) == (2, 3, 4, 5)


class TestModalCounts:
    def test_the_count_played_most_often_is_the_default(self) -> None:
        parse = StudyParse(
            tokens=(
                Play(phrase_id=0, ticks=4, transpose=0, default=False),
                Play(phrase_id=0, ticks=8, transpose=2, default=False),
                Play(phrase_id=0, ticks=4, transpose=0, default=True),
                Hold(ticks=1),
            ),
            costs=(0, 2, 5, 6, 7),
        )

        assert modal_counts((parse,), 2) == (4, 0)

    def test_a_tie_takes_the_shorter_count(self) -> None:
        parse = StudyParse(
            tokens=(
                Play(phrase_id=0, ticks=8, transpose=0, default=False),
                Play(phrase_id=0, ticks=4, transpose=0, default=False),
            ),
            costs=(0, 2, 4),
        )

        assert modal_counts((parse,), 1) == (4,)


class TestTheReferenceHoldsTheSandboxToTheCodec:
    song = _song(SONG_TICKS)
    compressed = compress_baseline(song)

    def test_the_baseline_parse_costs_what_the_codec_wrote(self) -> None:
        read = reference(self.song, self.compressed)

        assert [parse.size for parse in read.baseline] == [len(stream) for stream in self.compressed.streams]

    def test_a_stream_priced_differently_stops_the_study(self) -> None:
        read = reference(self.song, self.compressed)
        tampered = self.compressed.model_copy(
            update={"streams": PlaneOrder.across([stream + b"\x00" for stream in self.compressed.streams])}
        )

        with pytest.raises(ValueError, match="parted from the production parser"):
            verify_baseline(read.baseline, tampered)

    @pytest.mark.parametrize("entry", GRAMMAR_VARIANTS, ids=lambda entry: entry.name)
    def test_every_grammar_plays_back_and_adds_no_bytes_over_a_small_table(self, entry: GrammarVariant) -> None:
        read = reference(self.song, self.compressed)

        encoding = encode_grammar(read, entry.grammar)

        assert encoding.lossless
        assert encoding.written is None
        assert sum(encoding.streams) <= sum(len(stream) for stream in self.compressed.streams)

    @pytest.mark.parametrize("entry", GRAMMAR_VARIANTS, ids=lambda entry: entry.name)
    def test_a_plane_holding_zero_throughout_is_absent_under_every_grammar(self, entry: GrammarVariant) -> None:
        read = reference(self.song, self.compressed)

        encoding = encode_grammar(read, entry.grammar)

        assert [encoding.streams[plane] for plane in range(2, PLANE_COUNT, 3)] == [0, 0, 0]
