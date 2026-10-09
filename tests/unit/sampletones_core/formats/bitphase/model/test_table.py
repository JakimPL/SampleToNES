from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_core.formats.bitphase.model.table import BitphaseTable
from sampletones_core.formats.bitphase.specification.instruments import LOOP_FROM_START
from tests.suite.base import BaseTestSuite
from tests.suite.bitphase import LoadedTable
from tests.suite.case import BaseRegularTestCase

STEPS: Final[Tuple[int, ...]] = (0, 4, 7, 12, 7, 4)
MIDDLE_LOOP: Final[int] = 3
HELD_LOOP: Final[int] = len(STEPS) - 1
TICKS_PLAYED: Final[int] = 40
SHIFT: Final[int] = -5
TABLE_ID: Final[int] = 7
NAME: Final[str] = "Moved"


def table(loop: int) -> BitphaseTable:
    return BitphaseTable(id=0, rows=STEPS, loop=loop, name="Contour")


def engine_step(source: BitphaseTable, tick: int) -> int:
    """The step Bitphase's own reading of a table plays on a tick, from the suite's copy of the engine."""
    loaded = LoadedTable(id=source.id, loop=source.loop, name=source.name, rows=list(source.rows), additive=False)
    return loaded.step(tick)


class TestTheStepATableStandsAt(BaseTestSuite):
    """Playback advances a table a step per tick and circles from its loop, from the first step where
    the loop stands at the start, so the step a transpose row places its table at is the one the
    engine would have reached.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        loop: int

    test_cases: Tuple["TestTheStepATableStandsAt.TestCase", ...] = (
        TestCase(label="circling whole", loop=LOOP_FROM_START),
        TestCase(label="circling from the middle", loop=MIDDLE_LOOP),
        TestCase(label="holding the last step", loop=HELD_LOOP),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_step_is_the_one_the_engine_plays(self, test_case: "TestTheStepATableStandsAt.TestCase") -> None:
        source = table(test_case.loop)

        assert [source.rows[source.position_at(tick)] for tick in range(TICKS_PLAYED)] == [
            engine_step(source, tick) for tick in range(TICKS_PLAYED)
        ]


class TestAMovedTable(BaseTestSuite):
    """A moved table plays this table's steps moved by the shift from the step it opens on, so a
    transpose row reaching a step no ornament position names still sounds where the note stood.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        loop: int
        start: int

    test_cases: Tuple["TestAMovedTable.TestCase", ...] = (
        TestCase(label="opening on the first step", loop=MIDDLE_LOOP, start=0),
        TestCase(label="opening before the loop", loop=MIDDLE_LOOP, start=MIDDLE_LOOP - 1),
        TestCase(label="opening past the loop", loop=MIDDLE_LOOP, start=MIDDLE_LOOP + 1),
        TestCase(label="opening within a whole circle", loop=LOOP_FROM_START, start=MIDDLE_LOOP),
        TestCase(label="opening on a held step", loop=HELD_LOOP, start=HELD_LOOP),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_it_plays_what_the_table_plays_from_its_start(self, test_case: "TestAMovedTable.TestCase") -> None:
        source = table(test_case.loop)
        moved = source.moved(table_id=TABLE_ID, shift=SHIFT, start=test_case.start, name=NAME)

        assert [engine_step(moved, tick) for tick in range(TICKS_PLAYED)] == [
            engine_step(source, test_case.start + tick) + SHIFT for tick in range(TICKS_PLAYED)
        ]

    def test_it_takes_the_id_and_the_name_it_is_given(self) -> None:
        moved = table(MIDDLE_LOOP).moved(table_id=TABLE_ID, shift=SHIFT, start=0, name=NAME)

        assert (moved.id, moved.name) == (TABLE_ID, NAME)
