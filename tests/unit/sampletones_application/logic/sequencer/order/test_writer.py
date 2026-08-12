from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.order import (
    OrderBlockReader,
    OrderBlockWriter,
    SequencerOrderLogic,
)
from sampletones_application.view_model.sequencer.region import OrderCell, OrderRegion
from sampletones_core.constants.enums import GeneratorName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.sequencer import fill_order, parse_order_block, render_order

SILENT = ".. .. .."


@dataclass(frozen=True, kw_only=True)
class Table:
    """A three-position order, the state every paste case starts from."""

    controller: ProjectController
    logic: SequencerOrderLogic
    writer: OrderBlockWriter


@pytest.fixture
def table() -> Table:
    """An order short enough for a case to state whole, every channel silent to begin with."""
    controller = ProjectController(ProjectManager())
    logic = SequencerOrderLogic(controller)
    fill_order(
        logic,
        (
            SILENT,
            SILENT,
            SILENT,
            SILENT,
        ),
    )
    return Table(
        controller=controller,
        logic=logic,
        writer=OrderBlockWriter(logic),
    )


def _row(generator: Optional[GeneratorName]) -> int:
    return CHANNEL_AXIS.index(generator)


class TestPaste(BaseTestSuite):
    """What a block writes where it lands, stated as the whole order it leaves behind.

    A block carries the offsets it was read at while the cell it is written from supplies the row
    and the position it begins at, so every case states its origin as that pair.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        block: Tuple[str, ...]
        origin: OrderCell
        expected: Tuple[str, ...]
        order: Tuple[str, ...] = ()

    test_cases = (
        TestCase(
            label="a block lands at the cell it is written from",
            block=("07 08",),
            origin=OrderCell(generator=GeneratorName.PULSE2, position=1),
            expected=(
                SILENT,
                ".. 07 08",
                SILENT,
                SILENT,
            ),
        ),
        TestCase(
            label="a block through the master row reaches every channel",
            block=("05",),
            origin=OrderCell(generator=None, position=0),
            expected=(
                "05 .. ..",
                "05 .. ..",
                "05 .. ..",
                "05 .. ..",
            ),
        ),
        TestCase(
            label="a channel beneath the master row overwrites what it settled",
            block=(
                "05",
                "06",
            ),
            origin=OrderCell(generator=None, position=0),
            expected=(
                "06 .. ..",
                "05 .. ..",
                "05 .. ..",
                "05 .. ..",
            ),
        ),
        TestCase(
            label="a block read from the master row writes one channel when written to one",
            block=("05",),
            origin=OrderCell(generator=GeneratorName.TRIANGLE, position=2),
            expected=(
                SILENT,
                SILENT,
                ".. .. 05",
                SILENT,
            ),
        ),
        TestCase(
            label="a mixed cell leaves its target as it stands while its neighbours take theirs",
            order=(
                "01 02 03",
                SILENT,
                SILENT,
                SILENT,
            ),
            block=("09 ? 0A",),
            origin=OrderCell(generator=GeneratorName.PULSE1, position=0),
            expected=(
                "09 02 0A",
                SILENT,
                SILENT,
                SILENT,
            ),
        ),
        TestCase(
            label="an empty cell silences the slot it lands on",
            order=(
                "01 02 03",
                SILENT,
                SILENT,
                SILENT,
            ),
            block=(".. ..",),
            origin=OrderCell(generator=GeneratorName.PULSE1, position=0),
            expected=(
                ".. .. 03",
                SILENT,
                SILENT,
                SILENT,
            ),
        ),
        TestCase(
            label="the rows a block carries past the last channel are left out",
            block=(
                "01",
                "02",
                "03",
            ),
            origin=OrderCell(generator=GeneratorName.TRIANGLE, position=0),
            expected=(
                SILENT,
                SILENT,
                "01 .. ..",
                "02 .. ..",
            ),
        ),
        TestCase(
            label="a master row written to the last channel keeps that channel alone",
            block=(
                "01",
                "02",
            ),
            origin=OrderCell(generator=GeneratorName.NOISE, position=0),
            expected=(
                SILENT,
                SILENT,
                SILENT,
                "01 .. ..",
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_order_after_a_paste(
        self,
        table: Table,
        test_case: TestCase,
    ) -> None:
        fill_order(table.logic, test_case.order)

        table.writer.write(parse_order_block(test_case.block), test_case.origin)

        assert render_order(table.logic) == test_case.expected


class TestGrowth(BaseTestSuite):
    """How far a paste past the order's end grows it, which is to the last position it writes at."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        block: Tuple[str, ...]
        origin: OrderCell
        expected: Tuple[str, ...]

    test_cases = (
        TestCase(
            label="a block reaching past the end appends exactly the positions it writes",
            block=("01 02 03",),
            origin=OrderCell(generator=GeneratorName.PULSE1, position=2),
            expected=(
                ".. .. 01 02 03",
                ".. .. .. .. ..",
                ".. .. .. .. ..",
                ".. .. .. .. ..",
            ),
        ),
        TestCase(
            label="a column the block says nothing about appends no position",
            block=("01 ? ?",),
            origin=OrderCell(generator=GeneratorName.PULSE1, position=2),
            expected=(
                ".. .. 01",
                SILENT,
                SILENT,
                SILENT,
            ),
        ),
        TestCase(
            label="a column the block silences appends the position it silences",
            block=("01 ? ..",),
            origin=OrderCell(generator=GeneratorName.PULSE1, position=2),
            expected=(
                ".. .. 01 .. ..",
                ".. .. .. .. ..",
                ".. .. .. .. ..",
                ".. .. .. .. ..",
            ),
        ),
        TestCase(
            label="the rows a block loses at the last channel take their growth with them",
            block=(
                "01 ?",
                "?  02",
            ),
            origin=OrderCell(generator=GeneratorName.NOISE, position=2),
            expected=(
                SILENT,
                SILENT,
                SILENT,
                ".. .. 01",
            ),
        ),
        TestCase(
            label="a wholly mixed block leaves the order the length it was",
            block=("? ? ?",),
            origin=OrderCell(generator=GeneratorName.PULSE1, position=2),
            expected=(
                SILENT,
                SILENT,
                SILENT,
                SILENT,
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_order_after_a_paste_past_its_end(
        self,
        table: Table,
        test_case: TestCase,
    ) -> None:
        table.writer.write(parse_order_block(test_case.block), test_case.origin)

        assert render_order(table.logic) == test_case.expected


class TestClear:
    """What a delete silences, which is every cell its region covers and nothing beside."""

    def test_a_region_silences_the_cells_it_covers(self, table: Table) -> None:
        fill_order(
            table.logic,
            (
                "01 02 03",
                "01 02 03",
                "01 02 03",
                "01 02 03",
            ),
        )

        table.writer.clear(
            OrderRegion(
                first_row=_row(GeneratorName.PULSE2),
                last_row=_row(GeneratorName.TRIANGLE),
                first_position=0,
                last_position=1,
            )
        )

        assert render_order(table.logic) == (
            "01 02 03",
            ".. .. 03",
            ".. .. 03",
            "01 02 03",
        )

    def test_a_region_over_the_master_row_silences_every_channel(self, table: Table) -> None:
        fill_order(
            table.logic,
            (
                "01 02 03",
                "01 02 03",
                "01 02 03",
                "01 02 03",
            ),
        )

        table.writer.clear(
            OrderRegion(
                first_row=_row(None),
                last_row=_row(None),
                first_position=1,
                last_position=1,
            )
        )

        assert render_order(table.logic) == (
            "01 .. 03",
            "01 .. 03",
            "01 .. 03",
            "01 .. 03",
        )

    def test_a_delete_leaves_the_order_the_length_it_was(self, table: Table) -> None:
        """Emptying the frames at the end leaves them standing as silent ones."""
        fill_order(
            table.logic,
            (
                "01 02 03",
                "01 02 03",
                "01 02 03",
                "01 02 03",
            ),
        )

        table.writer.clear(
            OrderRegion(
                first_row=_row(None),
                last_row=_row(GeneratorName.NOISE),
                first_position=0,
                last_position=2,
            )
        )

        assert table.logic.position_count() == 3


class TestRoundTrip:
    """Reading a region, silencing it and writing the block back leaves the order it came from."""

    def test_a_block_written_back_at_its_origin_restores_the_order(self, table: Table) -> None:
        fill_order(
            table.logic,
            (
                "01 02 03",
                "01 04 03",
                ".. 02 03",
                "01 02 ..",
            ),
        )
        before = render_order(table.logic)
        region = OrderRegion(
            first_row=_row(GeneratorName.PULSE1),
            last_row=_row(GeneratorName.NOISE),
            first_position=0,
            last_position=2,
        )
        block = OrderBlockReader(table.logic).read(region)

        table.writer.clear(region)
        table.writer.write(block, OrderCell(generator=GeneratorName.PULSE1, position=0))

        assert render_order(table.logic) == before
