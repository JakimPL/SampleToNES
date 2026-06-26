from typing import Optional

import pytest

from sampletones_application.view_model.sequencer.samples import MoveDirection


@pytest.mark.parametrize(
    "direction, position, count, expected",
    [
        (MoveDirection.UP, 2, 5, 1),
        (MoveDirection.UP, 0, 5, None),
        (MoveDirection.DOWN, 2, 5, 3),
        (MoveDirection.DOWN, 4, 5, None),
        (MoveDirection.TOP, 3, 5, 0),
        (MoveDirection.TOP, 0, 5, None),
        (MoveDirection.BOTTOM, 1, 5, 4),
        (MoveDirection.BOTTOM, 4, 5, None),
        (MoveDirection.UP, 0, 1, None),
        (MoveDirection.DOWN, 0, 1, None),
        (MoveDirection.TOP, 0, 1, None),
        (MoveDirection.BOTTOM, 0, 1, None),
    ],
)
def test_move_direction_target(
    direction: MoveDirection,
    position: int,
    count: int,
    expected: Optional[int],
) -> None:
    assert direction.target(position, count) == expected
