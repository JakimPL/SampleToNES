from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_application.logic.sequencer.tracker.context import (
    ContextRows,
    FrameRows,
    rows_after,
    rows_before,
)
from sampletones_application.view_model.sequencer.tracker import SequencerRowViewModel
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

Position = Tuple[int, int]


def _frames_of(lengths: Tuple[int, ...]) -> FrameRows:
    """Reads a song whose frames hold ``lengths`` rows each, every row blank."""

    def read(frame_index: int) -> Tuple[SequencerRowViewModel, ...]:
        return tuple(
            SequencerRowViewModel(
                index=index,
                cells={},
                sample_channels=frozenset(),
                carried_channels=frozenset(),
            )
            for index in range(lengths[frame_index])
        )

    return read


def _positions(rows: ContextRows) -> Tuple[Position, ...]:
    """Where each gathered row stands in the song: its frame, then its row in that frame."""
    return tuple((row.frame_index, row.row.index) for row in rows)


class TestTheRowsBeforeAFrame(BaseTestSuite):
    """The rows leading into a frame are the song's own, gathered back across as many frames as it takes."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        lengths: Tuple[int, ...]
        frame_index: int
        reach: int
        expected: Tuple[Position, ...]

    test_cases = (
        TestCase(
            label="the previous frame's last rows",
            lengths=(4, 4, 4),
            frame_index=1,
            reach=2,
            expected=((0, 2), (0, 3)),
        ),
        TestCase(
            label="nothing before the first frame",
            lengths=(4, 4),
            frame_index=0,
            reach=2,
            expected=(),
        ),
        TestCase(
            label="a short frame gives all of its rows and the one before it the rest",
            lengths=(4, 2, 2),
            frame_index=2,
            reach=3,
            expected=((0, 3), (1, 0), (1, 1)),
        ),
        TestCase(
            label="the song's start ends the walk",
            lengths=(2, 4),
            frame_index=1,
            reach=3,
            expected=((0, 0), (0, 1)),
        ),
        TestCase(
            label="frames of different lengths",
            lengths=(3, 5, 4),
            frame_index=2,
            reach=6,
            expected=((0, 2), (1, 0), (1, 1), (1, 2), (1, 3), (1, 4)),
        ),
        TestCase(
            label="no reach",
            lengths=(4, 4),
            frame_index=1,
            reach=0,
            expected=(),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rows_gathered(self, test_case: TestCase) -> None:
        rows = rows_before(test_case.frame_index, test_case.reach, _frames_of(test_case.lengths))

        assert _positions(rows) == test_case.expected


class TestTheRowsAfterAFrame(BaseTestSuite):
    """The rows following a frame are the song's own, gathered on across as many frames as it takes."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        lengths: Tuple[int, ...]
        frame_index: int
        reach: int
        expected: Tuple[Position, ...]

    test_cases = (
        TestCase(
            label="the next frame's first rows",
            lengths=(4, 4, 4),
            frame_index=1,
            reach=2,
            expected=((2, 0), (2, 1)),
        ),
        TestCase(
            label="nothing after the last frame",
            lengths=(4, 4),
            frame_index=1,
            reach=2,
            expected=(),
        ),
        TestCase(
            label="a short frame gives all of its rows and the one after it the rest",
            lengths=(4, 2, 2),
            frame_index=0,
            reach=3,
            expected=((1, 0), (1, 1), (2, 0)),
        ),
        TestCase(
            label="the song's end ends the walk",
            lengths=(4, 2),
            frame_index=0,
            reach=3,
            expected=((1, 0), (1, 1)),
        ),
        TestCase(
            label="no reach",
            lengths=(4, 4),
            frame_index=0,
            reach=0,
            expected=(),
        ),
        TestCase(
            label="an order holding no frame",
            lengths=(),
            frame_index=0,
            reach=2,
            expected=(),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_rows_gathered(self, test_case: TestCase) -> None:
        rows = rows_after(
            test_case.frame_index,
            len(test_case.lengths),
            test_case.reach,
            _frames_of(test_case.lengths),
        )

        assert _positions(rows) == test_case.expected
