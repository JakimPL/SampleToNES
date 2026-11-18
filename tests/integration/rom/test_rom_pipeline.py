from typing import Dict, Final

import pytest

from sampletones_core.constants.enums import ALL_CHANNELS
from sampletones_core.formats.binary import BinaryReader
from sampletones_core.project.voices.sample import Sample
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.containers.nsf import NSFContainer
from sampletones_player.export.containers.rom import ROMContainer
from sampletones_player.export.program import Program
from sampletones_player.shell.image import ShellImage
from sampletones_player.shell.patterns import load_patterns
from sampletones_player.song import Song
from sampletones_player.specification.memory import NMI_VECTOR, PROGRAM_SIZE
from sampletones_player.specification.nsf import HEADER_SIZE
from sampletones_player.specification.program import PROGRAM_BLOCK_SIZE
from sampletones_player.specification.rom import ROM_HEADER_SIZE
from sampletones_player.specification.screen import PATTERNS_SIZE
from sampletones_player.specification.shell import VECTOR_COUNT, VECTORS_SIZE
from sampletones_tools.console.rom.machine import ROMConsole
from tests.integration.nsf.console.session import captured_run, play_calls_covering
from tests.integration.nsf.header import sample_information
from tests.integration.rom.session import CLEARED_MEMORY

NROM_FILE_SIZE: Final[int] = 40_976
PATTERNS_OFFSET: Final[int] = ROM_HEADER_SIZE + PROGRAM_SIZE
VECTORS_OFFSET: Final[int] = PATTERNS_OFFSET - VECTORS_SIZE


def program_of(sample: Sample) -> Program:
    return Program(
        information=sample_information(sample.name),
        channels=ALL_CHANNELS,
        loop_tick=None,
        scheme=CompressionScheme.SEARCH,
    )


@pytest.fixture
def rom_container(driver_image: DriverImage, shell_image: ShellImage) -> ROMContainer:
    return ROMContainer(driver_image, shell_image, load_patterns())


@pytest.fixture
def cartridge_file(rom_container: ROMContainer, song: Song, sample: Sample) -> bytes:
    """The cartridge the export writes for the sample."""
    return rom_container.to_bytes(song, program_of(sample))


@pytest.fixture
def nsf_file(driver_image: DriverImage, song: Song, sample: Sample) -> bytes:
    """The NSF the export writes for the same sample."""
    return NSFContainer(driver_image).to_bytes(song, program_of(sample))


class TestTheCartridgeCarriesWhatTheNSFCarries:
    """A cartridge is the NSF's driver and song with the shell behind them, at the addresses the NSF loads them."""

    def test_the_driver_is_the_one_the_nsf_carries(
        self, cartridge_file: bytes, nsf_file: bytes, driver_image: DriverImage
    ) -> None:
        driver = cartridge_file[ROM_HEADER_SIZE : ROM_HEADER_SIZE + len(driver_image.code)]

        assert driver == driver_image.code
        assert driver == nsf_file[HEADER_SIZE : HEADER_SIZE + len(driver_image.code)]

    def test_the_song_block_is_the_one_the_nsf_carries(
        self, cartridge_file: bytes, nsf_file: bytes, driver_image: DriverImage
    ) -> None:
        block = nsf_file[HEADER_SIZE + len(driver_image.code) :]
        start = ROM_HEADER_SIZE + len(driver_image.code)

        assert cartridge_file[start : start + len(block)] == block

    def test_the_vectors_point_into_the_shell(self, cartridge_file: bytes, shell_image: ShellImage) -> None:
        reader = BinaryReader(cartridge_file[VECTORS_OFFSET:PATTERNS_OFFSET])
        vectors = tuple(reader.read_uint16() for _ in range(VECTOR_COUNT))

        assert vectors == shell_image.vectors
        assert all(shell_image.start + PROGRAM_BLOCK_SIZE <= vector < NMI_VECTOR for vector in vectors)

    def test_the_file_takes_an_nrom_board_s_size(self, cartridge_file: bytes) -> None:
        """An NROM image is its 16-byte header, 32 KB of program and 8 KB of tiles, which is the format's own size."""
        assert len(cartridge_file) == ROM_HEADER_SIZE + PROGRAM_SIZE + PATTERNS_SIZE == NROM_FILE_SIZE

    def test_the_cartridge_sounds_what_the_nsf_sounds(self, cartridge_file: bytes, nsf_file: bytes, song: Song) -> None:
        calls = play_calls_covering(song)

        assert ROMConsole(cartridge_file, memory=CLEARED_MEMORY).trace(calls) == captured_run(nsf_file, calls)


class TestEverySampleReachesACartridge:
    def test_every_sample_s_cartridge_sounds_what_its_nsf_sounds(
        self, instrument_catalog: Dict[str, Sample], rom_container: ROMContainer, driver_image: DriverImage
    ) -> None:
        nsf_container = NSFContainer(driver_image)
        for sample in instrument_catalog.values():
            song = song_from_reconstruction(sample.reconstruction, loop_tick=None, scheme=CompressionScheme.SEARCH)
            program = program_of(sample)
            calls = play_calls_covering(song)

            cartridge_trace = ROMConsole(rom_container.to_bytes(song, program), memory=CLEARED_MEMORY).trace(calls)

            assert cartridge_trace == captured_run(nsf_container.to_bytes(song, program), calls)
