from typing import Optional

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.order import (
    OrderBlockReader,
    SequencerOrderLogic,
)
from sampletones_application.view_model.sequencer.region import OrderRegion
from sampletones_core.constants.enums import GeneratorName
from tests.suite.sequencer import fill_order

MASTER_ROW = CHANNEL_AXIS.index(None)
PULSE1_ROW = CHANNEL_AXIS.index(GeneratorName.PULSE1)
NOISE_ROW = CHANNEL_AXIS.index(GeneratorName.NOISE)


@pytest.fixture
def logic() -> SequencerOrderLogic:
    """The order logic the reader takes every entry through."""
    return SequencerOrderLogic(ProjectController(ProjectManager()))


@pytest.fixture
def reader(logic: SequencerOrderLogic) -> OrderBlockReader:
    return OrderBlockReader(logic)


def _row(
    generator: Optional[GeneratorName],
    *,
    last_position: int = 0,
) -> OrderRegion:
    """The region one whole row covers, out to ``last_position``."""
    row = CHANNEL_AXIS.index(generator)
    return OrderRegion(
        first_row=row,
        last_row=row,
        first_position=0,
        last_position=last_position,
    )


class TestChannelRow:
    """A channel answers for itself, so every one of its cells reaches the block definite."""

    def test_a_row_carries_the_indices_it_plays(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        fill_order(
            logic,
            (
                "00 01 02",
                ".. .. ..",
                ".. .. ..",
                ".. .. ..",
            ),
        )

        block = reader.read(_row(GeneratorName.PULSE1, last_position=2))

        assert block.entries == {(0, 0): 0, (0, 1): 1, (0, 2): 2}

    def test_a_silent_cell_carries_its_silence(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        """A slot playing nothing reads as the empty cell it shows, which a paste writes as silence."""
        fill_order(
            logic,
            (
                "00",
                "00",
                "00",
                "..",
            ),
        )

        block = reader.read(_row(GeneratorName.NOISE))

        assert block.entries == {(0, 0): None}


class TestMasterRow:
    """The master row answers for every channel, so it carries what they agree on and nothing else."""

    def test_a_position_its_channels_share_carries_the_index(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        fill_order(
            logic,
            (
                "03",
                "03",
                "03",
                "03",
            ),
        )

        block = reader.read(_row(None))

        assert block.entries == {(0, 0): 3}

    def test_a_position_every_channel_leaves_silent_carries_that_silence(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        """Silence is a reading the channels agree on, so it writes where a mixed cell would not."""
        fill_order(
            logic,
            (
                ".. ..",
                ".. ..",
                ".. ..",
                ".. ..",
            ),
        )

        block = reader.read(_row(None, last_position=1))

        assert block.entries == {(0, 0): None, (0, 1): None}

    def test_a_position_its_channels_disagree_over_is_left_out(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        fill_order(
            logic,
            (
                "00 04",
                "00 05",
                "00 04",
                "00 04",
            ),
        )

        block = reader.read(_row(None, last_position=1))

        assert block.entries == {(0, 0): 0}


class TestExtent:
    """A block states the rectangle it was read at, which a mixed edge column cannot take away."""

    def test_a_region_carries_the_shape_it_covers(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        fill_order(
            logic,
            (
                "00 01 02",
                "00 01 02",
                "00 01 02",
                "00 01 02",
            ),
        )

        block = reader.read(
            OrderRegion(
                first_row=MASTER_ROW,
                last_row=NOISE_ROW,
                first_position=1,
                last_position=2,
            )
        )

        assert (block.row_count, block.position_count) == (5, 2)

    def test_offsets_run_from_the_cell_the_region_begins_at(
        self,
        logic: SequencerOrderLogic,
        reader: OrderBlockReader,
    ) -> None:
        fill_order(
            logic,
            (
                "00 01 02",
                "00 01 03",
                "00 01 02",
                "00 01 02",
            ),
        )

        block = reader.read(
            OrderRegion(
                first_row=PULSE1_ROW,
                last_row=CHANNEL_AXIS.index(GeneratorName.PULSE2),
                first_position=2,
                last_position=2,
            )
        )

        assert block.entries == {(0, 0): 2, (1, 0): 3}
