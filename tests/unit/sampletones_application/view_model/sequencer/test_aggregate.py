from typing import Set

import pytest

from sampletones_application.view_model.sequencer.aggregate import aggregate_labels
from sampletones_shared.constants.symbols import MIXED

_DEFAULT = ".."


@pytest.mark.parametrize(
    "values, expected",
    [
        (set(), _DEFAULT),
        ({"05"}, "05"),
        ({"05", "07"}, MIXED),
        ({"05", "05"}, "05"),
        ({"05", "07", "09"}, MIXED),
    ],
)
def test_aggregate_labels(values: Set[str], expected: str) -> None:
    assert aggregate_labels(values, default=_DEFAULT) == expected
