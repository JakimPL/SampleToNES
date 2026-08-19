from typing import Any, Dict, Final

import pytest

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.driver import (
    INIT_ADDRESS,
    JUMP_ABSOLUTE_OPCODE,
    LOAD_ADDRESS,
    MAX_ADDRESS,
    PLAY_ADDRESS,
)
from tests.suite.base import BaseTestSuite

RETURN_OPCODE: Final[int] = 0x60
JUMP_TABLE: Final[bytes] = bytes((JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, JUMP_ABSOLUTE_OPCODE, 0x00, 0x80))
CODE: Final[bytes] = JUMP_TABLE + bytes((RETURN_OPCODE,))


def image_fields(code: bytes = CODE, **overrides: int) -> Dict[str, Any]:
    addresses = {
        "load": LOAD_ADDRESS,
        "init": INIT_ADDRESS,
        "play": PLAY_ADDRESS,
        "song": LOAD_ADDRESS + len(code),
    }
    addresses.update(overrides)
    return {"code": code, "addresses": DriverAddresses(**addresses)}


class TestTheCommittedDriver(BaseTestSuite):
    """The driver the package ships, held to the contract the exporter reads it through."""

    def test_the_driver_loads(self) -> None:
        assert DriverImage.load().code

    def test_the_song_begins_where_the_code_ends(self) -> None:
        image = DriverImage.load()
        assert image.addresses.song == image.addresses.load + len(image.code)

    def test_the_routines_answer_where_the_specification_states(self) -> None:
        image = DriverImage.load()
        assert (image.addresses.init, image.addresses.play) == (INIT_ADDRESS, PLAY_ADDRESS)

    def test_the_image_leads_with_a_jump_to_each_routine(self) -> None:
        assert DriverImage.load().code[: len(JUMP_TABLE) : 3] == bytes((JUMP_ABSOLUTE_OPCODE,) * 2)


class TestTheImageContract(BaseTestSuite):
    """What an image must lay out for the exporter to place a song behind the driver."""

    def test_a_song_address_past_the_code_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="the song belongs at"):
            DriverImage(**image_fields(song=LOAD_ADDRESS + len(CODE) + 1))

    def test_a_play_routine_outside_the_code_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="the play routine lies at"):
            DriverImage(**image_fields(play=LOAD_ADDRESS + len(CODE)))

    def test_an_init_routine_before_the_load_address_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="the init routine lies at"):
            DriverImage(**image_fields(init=LOAD_ADDRESS - 1))

    def test_an_image_that_leads_with_anything_but_a_jump_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="rather than the jump"):
            DriverImage(**image_fields(code=bytes((RETURN_OPCODE,)) * len(CODE)))

    def test_an_empty_image_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            DriverImage(**image_fields(code=b""))

    def test_an_address_past_the_bus_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            DriverImage(**image_fields(play=MAX_ADDRESS + 1))
