from typing import Optional

import pytest

from sampletones_application.view_model.sequencer.move import MoveDirection


@pytest.mark.parametrize(
    "direction, position, count, expected",
    [
        (MoveDirection.PREVIOUS, 2, 5, 1),
        (MoveDirection.PREVIOUS, 0, 5, None),
        (MoveDirection.NEXT, 2, 5, 3),
        (MoveDirection.NEXT, 4, 5, None),
        (MoveDirection.FIRST, 3, 5, 0),
        (MoveDirection.FIRST, 0, 5, None),
        (MoveDirection.LAST, 1, 5, 4),
        (MoveDirection.LAST, 4, 5, None),
        (MoveDirection.PREVIOUS, 0, 1, None),
        (MoveDirection.NEXT, 0, 1, None),
        (MoveDirection.FIRST, 0, 1, None),
        (MoveDirection.LAST, 0, 1, None),
    ],
)
def test_move_direction_target(
    direction: MoveDirection,
    position: int,
    count: int,
    expected: Optional[int],
) -> None:
    assert direction.target(position, count) == expected
