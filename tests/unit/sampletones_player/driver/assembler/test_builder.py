import shutil
from pathlib import Path
from typing import Final

import pytest

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.assembler.builder import build_driver, verify_addresses
from sampletones_player.driver.assembler.toolchain import ASSEMBLER
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.driver import (
    DRIVER_CODE_NAME,
    JUMP_ABSOLUTE_OPCODE,
    JUMP_INSTRUCTION_SIZE,
    LOAD_ADDRESS,
)
from sampletones_shared.exceptions import DriverBuildError
from tests.suite.base import BaseTestSuite

DISPLACEMENT: Final[int] = 0x0100
RETURN_OPCODE: Final[int] = 0x60
CODE: Final[bytes] = bytes((JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, RETURN_OPCODE))

cc65_installed = pytest.mark.skipif(shutil.which(ASSEMBLER) is None, reason="cc65 assembles the driver")


@pytest.fixture(name="built_driver", scope="module")
def fixture_built_driver(tmp_path_factory: pytest.TempPathFactory) -> DriverImage:
    return build_driver(tmp_path_factory.mktemp("driver"))


class TestTheLayoutABuildProduces(BaseTestSuite):
    """A build's own layout, held to the addresses the exporter reads the driver through."""

    @staticmethod
    def displaced_image(displacement: int) -> DriverImage:
        load = LOAD_ADDRESS + displacement
        addresses = DriverAddresses(
            load=load,
            init=load,
            play=load + JUMP_INSTRUCTION_SIZE,
            song=load + len(CODE),
        )
        return DriverImage(code=CODE, addresses=addresses)

    def test_a_displaced_image_names_the_load_address_that_moved(self) -> None:
        with pytest.raises(DriverBuildError, match="load at"):
            verify_addresses(self.displaced_image(DISPLACEMENT))

    def test_a_displaced_image_names_the_song_address_that_moved(self) -> None:
        with pytest.raises(DriverBuildError, match="song at"):
            verify_addresses(self.displaced_image(DISPLACEMENT))


@cc65_installed
class TestTheDriverBuild(BaseTestSuite):
    """The committed driver against the sources it is built from."""

    def test_the_committed_driver_matches_its_sources(self, built_driver: DriverImage) -> None:
        message = f"{DRIVER_CODE_NAME} is behind its sources: run `make player`"
        assert built_driver.code == DriverImage.load().code, message

    def test_the_linker_lays_the_driver_out_where_it_is_declared(self, built_driver: DriverImage) -> None:
        assert built_driver.addresses == DriverImage.load().addresses

    def test_the_build_writes_the_image_it_answers_with(self, tmp_path: Path) -> None:
        built = build_driver(tmp_path)
        assert (tmp_path / DRIVER_CODE_NAME).read_bytes() == built.code
