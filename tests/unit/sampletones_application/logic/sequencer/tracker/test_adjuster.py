from dataclasses import dataclass
from typing import Final, Optional, Tuple

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerRegionAdjuster,
)
from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.sequencer import fill_frame, render_frame, sample_reconstruction

FRAME_ROWS: Final[int] = 3
EMPTY: Final[str] = ".. ... . | .. ... . | .. ... . | .. ... ."
LEAD: Final[str] = "00"


@dataclass(frozen=True, kw_only=True)
class Grid:
    """A three-row frame with a sample over two channels, the state every case starts from."""

    controller: ProjectController
    logic: SequencerTrackerLogic
    adjuster: TrackerRegionAdjuster
    sample_ids: Tuple[str, ...]


@pytest.fixture
def grid() -> Grid:
    """A frame short enough for a case to state whole, holding a sample over two of the channels.

    Which channels a sample governs is what the sample column fans a shift out over, so a governed
    row and an ungoverned one both stand available to a case.
    """
    controller = ProjectController(ProjectManager())
    logic = SequencerTrackerLogic(controller)
    logic.set_rows_per_pattern(FRAME_ROWS)
    lead = controller.add_sample(
        sample_reconstruction([ChannelName.PULSE1, ChannelName.PULSE2]),
        name="lead",
    )
    return Grid(
        controller=controller,
        logic=logic,
        adjuster=TrackerRegionAdjuster(logic),
        sample_ids=(lead.id,),
    )


def _region(
    first: Tuple[Optional[ChannelName], SubColumn],
    last: Tuple[Optional[ChannelName], SubColumn],
    *,
    first_row: int = 0,
    last_row: int = 0,
) -> TrackerRegion:
    """The rectangle a pair of slots bounds, each stated as the column and subcolumn it addresses."""
    return TrackerRegion(
        first_row=first_row,
        last_row=last_row,
        first_slot=TrackerSlot(*first).flat_index,
        last_slot=TrackerSlot(*last).flat_index,
    )


class TestAdjustTranspose(BaseTestSuite):
    """Which cells a transpose shift reaches, stated as the whole frame it leaves behind.

    A shift acts on whole cells while a region names its edges as subcolumns, so each case states
    the subcolumns its region begins and ends on and reads the columns behind them in the result.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        region: TrackerRegion
        delta: int
        expected: Tuple[str, ...]
        frame: Tuple[str, ...] = ()

    test_cases = (
        TestCase(
            label="a cell alone shifts its own channel",
            region=_region(
                (ChannelName.PULSE1, SubColumn.INSTRUMENT),
                (ChannelName.PULSE1, SubColumn.INSTRUMENT),
            ),
            delta=1,
            expected=(
                ".. +01 . | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a region standing on another subcolumn still shifts the transpose",
            region=_region(
                (ChannelName.TRIANGLE, SubColumn.VOLUME),
                (ChannelName.TRIANGLE, SubColumn.VOLUME),
            ),
            delta=-1,
            expected=(
                ".. ... . | .. ... . | .. -01 . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a shift adds to the transpose a cell already holds",
            frame=(".. +02 . | .. ... . | .. ... . | .. ... .",),
            region=_region(
                (ChannelName.PULSE1, SubColumn.TRANSPOSE),
                (ChannelName.PULSE1, SubColumn.TRANSPOSE),
            ),
            delta=12,
            expected=(
                ".. +0E . | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a region across columns shifts each of them",
            region=_region(
                (ChannelName.PULSE2, SubColumn.VOLUME),
                (ChannelName.NOISE, SubColumn.INSTRUMENT),
            ),
            delta=1,
            expected=(
                ".. ... . | .. +01 . | .. +01 . | .. +01 .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a region across rows shifts each of them",
            region=_region(
                (ChannelName.PULSE1, SubColumn.INSTRUMENT),
                (ChannelName.PULSE1, SubColumn.INSTRUMENT),
                first_row=1,
                last_row=2,
            ),
            delta=2,
            expected=(
                EMPTY,
                ".. +02 . | .. ... . | .. ... . | .. ... .",
                ".. +02 . | .. ... . | .. ... . | .. ... .",
            ),
        ),
        TestCase(
            label="an ungoverned sample column reaches every channel",
            region=_region(
                (None, SubColumn.INSTRUMENT),
                (None, SubColumn.VOLUME),
            ),
            delta=3,
            expected=(
                ".. +03 . | .. +03 . | .. +03 . | .. +03 .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a governed sample column reaches the channels its sample uses",
            frame=(f"{LEAD} ... . | {LEAD} ... . | .. ... . | .. ... .",),
            region=_region(
                (None, SubColumn.INSTRUMENT),
                (None, SubColumn.VOLUME),
            ),
            delta=3,
            expected=(
                "00 +03 . | 00 +03 . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a channel covered beside the sample column moves a single step",
            frame=(f"{LEAD} ... . | {LEAD} ... . | .. ... . | .. ... .",),
            region=_region(
                (None, SubColumn.INSTRUMENT),
                (ChannelName.PULSE1, SubColumn.VOLUME),
            ),
            delta=1,
            expected=(
                "00 +01 . | 00 +01 . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a shift stops at the transpose range",
            frame=(".. +20 . | .. ... . | .. ... . | .. ... .",),
            region=_region(
                (ChannelName.PULSE1, SubColumn.TRANSPOSE),
                (ChannelName.PULSE1, SubColumn.TRANSPOSE),
            ),
            delta=12,
            expected=(
                ".. +24 . | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_frame_after_a_shift(
        self,
        grid: Grid,
        test_case: TestCase,
    ) -> None:
        fill_frame(grid.logic, test_case.frame, sample_ids=grid.sample_ids)

        grid.adjuster.adjust_transpose(test_case.region, test_case.delta)

        assert render_frame(grid.logic) == test_case.expected


class TestAdjustVolume(BaseTestSuite):
    """Which cells a volume shift reaches, read the same way a transpose shift is."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        region: TrackerRegion
        delta: int
        expected: Tuple[str, ...]
        frame: Tuple[str, ...] = ()

    test_cases = (
        TestCase(
            label="an unset cell steps down from full",
            region=_region(
                (ChannelName.PULSE1, SubColumn.INSTRUMENT),
                (ChannelName.PULSE1, SubColumn.INSTRUMENT),
            ),
            delta=-1,
            expected=(
                ".. ... E | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a coarse step moves the whole region",
            frame=(".. ... 8 | .. ... 8 | .. ... . | .. ... .",),
            region=_region(
                (ChannelName.PULSE1, SubColumn.VOLUME),
                (ChannelName.PULSE2, SubColumn.VOLUME),
            ),
            delta=-4,
            expected=(
                ".. ... 4 | .. ... 4 | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a shift stops at silence",
            frame=(".. ... 1 | .. ... . | .. ... . | .. ... .",),
            region=_region(
                (ChannelName.PULSE1, SubColumn.VOLUME),
                (ChannelName.PULSE1, SubColumn.VOLUME),
            ),
            delta=-4,
            expected=(
                ".. ... 0 | .. ... . | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
        TestCase(
            label="a channel covered beside the sample column moves a single step",
            frame=(f"{LEAD} ... 8 | {LEAD} ... 8 | .. ... . | .. ... .",),
            region=_region(
                (None, SubColumn.INSTRUMENT),
                (ChannelName.PULSE1, SubColumn.VOLUME),
            ),
            delta=-1,
            expected=(
                "00 ... 7 | 00 ... 7 | .. ... . | .. ... .",
                EMPTY,
                EMPTY,
            ),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_frame_after_a_shift(
        self,
        grid: Grid,
        test_case: TestCase,
    ) -> None:
        fill_frame(grid.logic, test_case.frame, sample_ids=grid.sample_ids)

        grid.adjuster.adjust_volume(test_case.region, test_case.delta)

        assert render_frame(grid.logic) == test_case.expected
