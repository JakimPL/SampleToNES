from typing import Final

from sampletones_core.reconstructions import Reconstruction
from tests.suite.performance import make_pulse_reconstruction
from tests.suite.timing import seconds

SHORT_DOCUMENT: Final[int] = 500
LONG_DOCUMENT: Final[int] = 5_000
GROWTH_ALLOWANCE: Final[float] = 2.0


def linear(one: float) -> float:
    """What the long document may cost, given the short one: its frames' share, and room for the reading."""
    return one * (LONG_DOCUMENT / SHORT_DOCUMENT) * GROWTH_ALLOWANCE


class TestADocumentCostsWhatItsFramesCost:
    """Storing and reading a reconstruction follows the frames it holds, each stored the way a list stores it."""

    def test_writing(self) -> None:
        short = make_pulse_reconstruction(count=SHORT_DOCUMENT)
        long = make_pulse_reconstruction(count=LONG_DOCUMENT)

        one = seconds(short.serialize)
        many = seconds(long.serialize)

        assert many < linear(one), f"{SHORT_DOCUMENT} frames: {one:.4f} s, {LONG_DOCUMENT} frames: {many:.4f} s"

    def test_reading(self) -> None:
        short = make_pulse_reconstruction(count=SHORT_DOCUMENT).serialize()
        long = make_pulse_reconstruction(count=LONG_DOCUMENT).serialize()

        one = seconds(lambda: Reconstruction.deserialize(short))
        many = seconds(lambda: Reconstruction.deserialize(long))

        assert many < linear(one), f"{SHORT_DOCUMENT} frames: {one:.4f} s, {LONG_DOCUMENT} frames: {many:.4f} s"
