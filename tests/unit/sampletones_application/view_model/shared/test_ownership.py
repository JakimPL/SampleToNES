from typing import Final, Tuple

import pytest

from sampletones_application.view_model.shared.ownership import (
    OwnershipLaneViewModel,
    OwnershipRunViewModel,
)
from sampletones_core.constants.enums import ChannelName

FIRST_STEM: Final[int] = 0
SECOND_STEM: Final[int] = 1


def _run(start_frame: int, end_frame: int, stem_id: int) -> OwnershipRunViewModel:
    return OwnershipRunViewModel(
        start_frame=start_frame,
        end_frame=end_frame,
        stem_id=stem_id,
        position=stem_id,
        heard=True,
    )


def _lane(*runs: OwnershipRunViewModel) -> OwnershipLaneViewModel:
    return OwnershipLaneViewModel(channel_name=ChannelName.PULSE1, runs=runs)


class TestTheStretchesUnderAReading:
    """A lane runs the length of its channel, and answers for the frames a reading draws.

    A channel's readings trim to their own lengths, so a lane handed whole to each of them would
    paint a stretch over frames that reading never drew.
    """

    def test_a_reading_as_long_as_the_channel_takes_every_stretch(self) -> None:
        lane = _lane(_run(0, 4, FIRST_STEM), _run(4, 10, SECOND_STEM))

        assert lane.up_to(10) == lane.runs

    def test_a_stretch_crossing_the_reading_ends_where_the_reading_does(self) -> None:
        lane = _lane(_run(0, 4, FIRST_STEM), _run(4, 10, SECOND_STEM))

        assert lane.up_to(6) == (_run(0, 4, FIRST_STEM), _run(4, 6, SECOND_STEM))

    def test_a_stretch_beyond_the_reading_stands_out_of_it(self) -> None:
        lane = _lane(_run(0, 4, FIRST_STEM), _run(4, 10, SECOND_STEM))

        assert lane.up_to(4) == (_run(0, 4, FIRST_STEM),)

    def test_a_reading_of_one_frame_keeps_the_stretch_over_it(self) -> None:
        lane = _lane(_run(0, 4, FIRST_STEM), _run(4, 10, SECOND_STEM))

        assert lane.up_to(1) == (_run(0, 1, FIRST_STEM),)

    def test_a_reading_writing_nothing_carries_no_stretch(self) -> None:
        lane = _lane(_run(0, 4, FIRST_STEM), _run(4, 10, SECOND_STEM))

        assert lane.up_to(0) == ()

    def test_a_lane_with_no_stretches_answers_with_none(self) -> None:
        assert _lane().up_to(10) == ()
