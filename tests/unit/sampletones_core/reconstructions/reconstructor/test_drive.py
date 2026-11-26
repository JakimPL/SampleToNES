from typing import Final

import numpy as np
import pytest

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.reconstructions.reconstructor.drive import driven_amplitudes, driven_powers, driven_variance
from tests.suite.base import BaseTestSuite

POWERS: Final[np.ndarray] = np.array([[1.0, 4.0, 0.0], [0.5, 2.0, 8.0]])
WAVEFORM: Final[np.ndarray] = np.array([0.5, -0.25, 0.0, 1.0])
VARIANCE: Final[float] = 0.36
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


class TestDrivenAmplitudes(BaseTestSuite):
    """A waveform read at a drive keeps the power ``driven_powers`` reads, its variance divided alike."""

    @pytest.mark.parametrize("drive", [LOUDER_DRIVE, SOFTER_DRIVE], ids=["louder", "softer"])
    def test_a_driven_waveform_holds_the_driven_power(self, drive: float) -> None:
        driven = driven_amplitudes(WAVEFORM, drive)

        assert np.square(driven) == pytest.approx(driven_powers(np.square(WAVEFORM), drive))

    @pytest.mark.parametrize("drive", [LOUDER_DRIVE, SOFTER_DRIVE], ids=["louder", "softer"])
    def test_a_driven_variance_is_the_variance_of_the_driven_waveform(self, drive: float) -> None:
        assert driven_variance(float(np.var(WAVEFORM)), drive) == pytest.approx(
            float(np.var(driven_amplitudes(WAVEFORM, drive)))
        )

    def test_at_unit_drive_the_amplitudes_and_the_variance_stand_as_they_are(self) -> None:
        assert np.array_equal(driven_amplitudes(WAVEFORM, UNIT_DRIVE), WAVEFORM)
        assert driven_variance(VARIANCE, UNIT_DRIVE) == VARIANCE
