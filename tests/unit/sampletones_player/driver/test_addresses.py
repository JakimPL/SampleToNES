from typing import Final

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.specification.driver import (
    INIT_ADDRESS,
    JUMP_INSTRUCTION_SIZE,
    LOAD_ADDRESS,
    PLAY_ADDRESS,
)
from sampletones_player.specification.nsf import PROGRAM_START
from tests.suite.base import BaseTestSuite

CODE_LENGTH: Final[int] = 512


class TestTheDeclaredAddresses(BaseTestSuite):
    """The addresses a driver answers at, which hold whatever the build produces."""

    def test_the_image_loads_where_the_program_area_begins(self) -> None:
        assert DriverAddresses.for_code(CODE_LENGTH).load == PROGRAM_START

    def test_the_routines_answer_where_the_specification_states(self) -> None:
        addresses = DriverAddresses.for_code(CODE_LENGTH)
        assert (addresses.init, addresses.play) == (INIT_ADDRESS, PLAY_ADDRESS)

    def test_the_entry_points_sit_one_jump_apart(self) -> None:
        addresses = DriverAddresses.for_code(CODE_LENGTH)
        assert addresses.play - addresses.init == JUMP_INSTRUCTION_SIZE

    def test_the_song_follows_the_code(self) -> None:
        assert DriverAddresses.for_code(CODE_LENGTH).song == LOAD_ADDRESS + CODE_LENGTH

    def test_a_longer_driver_moves_the_song_alone(self) -> None:
        shorter = DriverAddresses.for_code(CODE_LENGTH)
        longer = DriverAddresses.for_code(CODE_LENGTH * 2)
        assert (longer.load, longer.init, longer.play) == (shorter.load, shorter.init, shorter.play)
        assert longer.song > shorter.song
