from typing import Final

import numpy as np
import pytest

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.reconstructions.reconstructor.drive import driven_powers
from tests.suite.base import BaseTestSuite

POWERS: Final[np.ndarray] = np.array([[1.0, 4.0, 0.0], [0.5, 2.0, 8.0]])
LOUDER_DRIVE: Final[float] = 2.0
SOFTER_DRIVE: Final[float] = 0.5


class TestDrivenPowers(BaseTestSuite):
    """A channel at drive ``d`` reads each row at ``1 / d`` of its library amplitude, ``1 / d²`` of its power."""

    @pytest.mark.parametrize("drive", [LOUDER_DRIVE, SOFTER_DRIVE], ids=["louder", "softer"])
    def test_a_drive_reads_a_row_at_the_inverse_square_of_its_power(self, drive: float) -> None:
        driven = driven_powers(POWERS, drive)

        assert driven * drive**2 == pytest.approx(POWERS)

    def test_at_unit_drive_the_powers_stand_as_they_are(self) -> None:
        assert np.array_equal(driven_powers(POWERS, UNIT_DRIVE), POWERS)
