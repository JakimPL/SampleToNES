import pytest

from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.compression import PLANE_COUNT


def numbered(count: int) -> PlaneOrder:
    return PlaneOrder.across(bytes((plane,)) for plane in range(count))


class TestThePlanesAreNamedRatherThanNumbered:
    """The song block writes eight planes in one order, and each is reached by its own name."""

    def test_the_planes_take_the_names_the_song_block_writes_them_by(self) -> None:
        planes = numbered(PLANE_COUNT)
        assert planes.pulse1_control == bytes((0,))
        assert planes.noise_value == bytes((PLANE_COUNT - 1,))

    def test_a_run_of_planes_other_than_a_song_block_holds_is_refused(self) -> None:
        with pytest.raises(ValueError):
            numbered(PLANE_COUNT - 1)
