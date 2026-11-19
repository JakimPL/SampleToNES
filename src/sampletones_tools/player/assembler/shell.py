from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Final, List, Tuple

from sampletones_player.driver.image import DriverImage
from sampletones_player.shell.image import ShellImage
from sampletones_player.specification.driver import LOAD_ADDRESS
from sampletones_player.specification.shell import (
    ADDRESS_SPACE_END,
    SHELL_CODE_NAME,
    VECTORS_SIZE,
)
from sampletones_shared.exceptions import DriverBuildError
from sampletones_tools.player.assembler.builder import assemble_sources
from sampletones_tools.player.assembler.labels import address_of, addresses_of, read_labels
from sampletones_tools.player.assembler.layout import (
    ASSEMBLY_DIRECTORY,
    SHELL_CONFIGURATION,
    SHELL_SOURCE_NAMES,
    SOURCE_NAMES,
)
from sampletones_tools.player.assembler.toolchain import Toolchain

PROBE_START: Final[int] = 0xC000
UNWRITTEN_BYTE: Final[int] = 0xFF
PROGRAM_IMAGE_NAME: Final[str] = "program.bin"
LABELS_NAME: Final[str] = "program.labels"
PROGRAM_BLOCK_SYMBOL: Final[str] = "program_block"
SHELL_SEGMENT_SIZES: Final[Tuple[str, ...]] = ("__PROGRAM_SIZE__", "__PLAYER_SIZE__")


def build_shell(destination: Path, driver: DriverImage) -> ShellImage:
    """Assembles the shell with the driver it calls and writes it into ``destination``.

    The two are linked as the whole program a cartridge carries, so the shell reaches the driver's
    routines and memory by name. The shell ends at the top of the address space, and its start
    follows from its own length, so the link runs twice: once to measure the shell, and once to
    place it.

    Args:
        destination: The directory receiving ``shell.bin``.
        driver: The driver the package ships, which the linked program must carry byte for byte.

    Returns:
        ShellImage: The assembled shell.

    Raises:
        ToolchainMissingError: If the cc65 programs are absent from the system.
        DriverBuildError: If a program fails, or the linked program lays the driver out otherwise
            than ``driver`` states.
    """
    toolchain = Toolchain.locate()
    with TemporaryDirectory() as directory:
        work_directory = Path(directory)
        objects = assemble_sources(toolchain, ASSEMBLY_DIRECTORY, work_directory, (*SOURCE_NAMES, *SHELL_SOURCE_NAMES))
        _, measured = link_program(toolchain, objects, work_directory, PROBE_START)
        start = ADDRESS_SPACE_END - shell_length(measured)
        program, labels = link_program(toolchain, objects, work_directory, start)

    shell = verified_shell(program, labels, driver, start)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / SHELL_CODE_NAME).write_bytes(shell.code)
    return shell


def link_program(
    toolchain: Toolchain,
    objects: List[Path],
    work_directory: Path,
    start: int,
) -> Tuple[bytes, Dict[str, int]]:
    """Links the driver and the shell with the shell starting at ``start``.

    Returns:
        Tuple[bytes, Dict[str, int]]: The program area as the cartridge carries it, and the
        address of every symbol.

    Raises:
        DriverBuildError: If the linker reports a failure.
    """
    image = work_directory / PROGRAM_IMAGE_NAME
    labels = work_directory / LABELS_NAME
    toolchain.link(ASSEMBLY_DIRECTORY / SHELL_CONFIGURATION, objects, image, labels, start=start)
    return image.read_bytes(), read_labels(labels)


def shell_length(labels: Dict[str, int]) -> int:
    """The bytes the shell takes: its segments and the vectors closing them."""
    return sum(address_of(labels, symbol) for symbol in SHELL_SEGMENT_SIZES) + VECTORS_SIZE


def verified_shell(program: bytes, labels: Dict[str, int], driver: DriverImage, start: int) -> ShellImage:
    """Holds a linked program to the driver the package ships and cuts the shell out of it.

    Args:
        program: The program area the linker wrote.
        labels: The address of every symbol in it.
        driver: The driver the program must carry byte for byte.
        start: Where the shell was placed.

    Returns:
        ShellImage: The shell, from its program block to the vectors.

    Raises:
        DriverBuildError: If the driver, the room left for the song or the program block lie
            otherwise than a cartridge expects.
    """
    shell_offset = start - LOAD_ADDRESS
    song_room = program[len(driver.code) : shell_offset]
    for failed, problem in (
        (len(program) != ADDRESS_SPACE_END - LOAD_ADDRESS, f"the program area takes {len(program)} bytes"),
        (addresses_of(labels) != driver.addresses, "the driver is laid out at other addresses than the shipped one"),
        (program[: len(driver.code)] != driver.code, "the linked driver differs from the shipped one"),
        (any(byte != UNWRITTEN_BYTE for byte in song_room), "the room left for the song holds code"),
        (
            address_of(labels, PROGRAM_BLOCK_SYMBOL) != start,
            "the shell opens with something other than its program block",
        ),
    ):
        if failed:
            raise DriverBuildError(f"the cartridge program is laid out wrongly: {problem}")

    try:
        return ShellImage(code=program[shell_offset:])
    except ValueError as error:
        raise DriverBuildError(f"the assembled shell is malformed: {error}") from error
