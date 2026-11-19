import shutil
from pathlib import Path
from typing import Dict, Final

import pytest

from sampletones_player.driver.image import DriverImage
from sampletones_player.shell.image import ShellImage
from sampletones_player.specification.driver import LOAD_ADDRESS
from sampletones_player.specification.shell import ADDRESS_SPACE_END, SHELL_CODE_NAME
from sampletones_shared.exceptions import DriverBuildError
from sampletones_tools.player.assembler.labels import INIT_SYMBOL, LOAD_SYMBOL, PLAY_SYMBOL, SONG_SYMBOL
from sampletones_tools.player.assembler.shell import (
    PROGRAM_BLOCK_SYMBOL,
    UNWRITTEN_BYTE,
    build_shell,
    shell_length,
    verified_shell,
)
from sampletones_tools.player.assembler.toolchain import ASSEMBLER
from tests.suite.base import BaseTestSuite

STRAY_BYTE: Final[int] = 0xEA
PROGRAM_SIZE: Final[int] = 0x0123
PLAYER_SIZE: Final[int] = 0x0045
VECTORS_SIZE: Final[int] = 6

cc65_installed = pytest.mark.skipif(shutil.which(ASSEMBLER) is None, reason="cc65 assembles the shell")


@pytest.fixture(name="driver", scope="module")
def fixture_driver() -> DriverImage:
    return DriverImage.load()


@pytest.fixture(name="shell", scope="module")
def fixture_shell() -> ShellImage:
    return ShellImage.load()


def linked(driver: DriverImage, shell: ShellImage) -> bytes:
    """The program area a link of the shipped driver and shell lays out."""
    room = shell.start - LOAD_ADDRESS - len(driver.code)
    return driver.code + bytes([UNWRITTEN_BYTE]) * room + shell.code


def labels_of(driver: DriverImage, shell: ShellImage) -> Dict[str, int]:
    addresses = driver.addresses
    return {
        LOAD_SYMBOL: addresses.load,
        INIT_SYMBOL: addresses.init,
        PLAY_SYMBOL: addresses.play,
        SONG_SYMBOL: addresses.song,
        PROGRAM_BLOCK_SYMBOL: shell.start,
    }


class TestTheLengthOfAShell(BaseTestSuite):
    def test_it_sums_its_segments_and_the_vectors(self) -> None:
        labels = {"__PROGRAM_SIZE__": PROGRAM_SIZE, "__PLAYER_SIZE__": PLAYER_SIZE}

        assert shell_length(labels) == PROGRAM_SIZE + PLAYER_SIZE + VECTORS_SIZE

    def test_a_missing_segment_size_is_reported(self) -> None:
        with pytest.raises(DriverBuildError, match="__PLAYER_SIZE__"):
            shell_length({"__PROGRAM_SIZE__": PROGRAM_SIZE})


class TestALinkedProgram(BaseTestSuite):
    """A link of the shipped images, and the ways a program can depart from it."""

    def test_the_shipped_images_link_into_the_shipped_shell(self, driver: DriverImage, shell: ShellImage) -> None:
        program = linked(driver, shell)

        assert verified_shell(program, labels_of(driver, shell), driver, shell.start) == shell

    def test_a_driver_differing_from_the_shipped_one_is_refused(self, driver: DriverImage, shell: ShellImage) -> None:
        program = bytearray(linked(driver, shell))
        program[len(driver.code) - 1] ^= 0xFF

        with pytest.raises(DriverBuildError, match="differs"):
            verified_shell(bytes(program), labels_of(driver, shell), driver, shell.start)

    def test_code_in_the_room_left_for_the_song_is_refused(self, driver: DriverImage, shell: ShellImage) -> None:
        program = bytearray(linked(driver, shell))
        program[len(driver.code)] = STRAY_BYTE

        with pytest.raises(DriverBuildError, match="room left for the song"):
            verified_shell(bytes(program), labels_of(driver, shell), driver, shell.start)

    def test_a_program_block_away_from_the_start_is_refused(self, driver: DriverImage, shell: ShellImage) -> None:
        labels = {**labels_of(driver, shell), PROGRAM_BLOCK_SYMBOL: shell.start + 1}

        with pytest.raises(DriverBuildError, match="program block"):
            verified_shell(linked(driver, shell), labels, driver, shell.start)

    def test_a_driver_laid_out_at_other_addresses_is_refused(self, driver: DriverImage, shell: ShellImage) -> None:
        labels = {**labels_of(driver, shell), SONG_SYMBOL: driver.addresses.song + 1}

        with pytest.raises(DriverBuildError, match="other addresses"):
            verified_shell(linked(driver, shell), labels, driver, shell.start)

    def test_a_program_area_of_another_size_is_refused(self, driver: DriverImage, shell: ShellImage) -> None:
        with pytest.raises(DriverBuildError, match="program area"):
            verified_shell(linked(driver, shell)[1:], labels_of(driver, shell), driver, shell.start + 1)


@cc65_installed
class TestTheShellBuild(BaseTestSuite):
    """The committed shell against the sources it is built from."""

    def test_the_committed_shell_matches_its_sources(self, tmp_path: Path, driver: DriverImage) -> None:
        message = f"{SHELL_CODE_NAME} is behind its sources: run `uv run sampletones driver`"
        assert build_shell(tmp_path, driver) == ShellImage.load(), message

    def test_the_build_writes_the_shell_it_answers_with(self, tmp_path: Path, driver: DriverImage) -> None:
        built = build_shell(tmp_path, driver)

        assert (tmp_path / SHELL_CODE_NAME).read_bytes() == built.code

    def test_the_shell_finds_the_song_behind_the_driver(self, tmp_path: Path, driver: DriverImage) -> None:
        assert build_shell(tmp_path, driver).linked_song == driver.addresses.song

    def test_the_shell_ends_at_the_top_of_the_address_space(self, tmp_path: Path, driver: DriverImage) -> None:
        built = build_shell(tmp_path, driver)

        assert built.start + len(built.code) == ADDRESS_SPACE_END
