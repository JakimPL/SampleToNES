from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, List

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.assembler.labels import read_addresses
from sampletones_player.driver.assembler.layout import (
    INCLUDE_DIRECTORY,
    LINKER_CONFIGURATION,
    SOURCE_DIRECTORY,
    SOURCE_NAMES,
)
from sampletones_player.driver.assembler.toolchain import Toolchain
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.driver import DRIVER_CODE_NAME
from sampletones_shared.exceptions import DriverBuildError

LABELS_NAME: Final[str] = "driver.labels"
OBJECT_SUFFIX: Final[str] = ".o"


def build_driver(destination: Path) -> DriverImage:
    """Assembles the driver and writes the image into ``destination``.

    The image is held to the addresses the exporter reads it through before it reaches the
    directory, so a build either produces the driver the package ships or produces nothing.
    ``driver.s`` leads the sources because the linker lays a segment out in the order it receives
    the object files, and the entry points are the first bytes of the image.

    Args:
        destination: The directory receiving ``driver.bin``.

    Returns:
        DriverImage: The assembled bytes and the addresses the linker laid them out at.

    Raises:
        ToolchainMissingError: If the cc65 programs are absent from the system.
        DriverBuildError: If a program fails, or the layout departs from the one the driver is
            built to answer at.
    """
    toolchain = Toolchain.locate()
    with TemporaryDirectory() as directory:
        work_directory = Path(directory)
        objects = assemble_sources(toolchain, work_directory)
        assembled = work_directory / DRIVER_CODE_NAME
        labels = work_directory / LABELS_NAME
        toolchain.link(LINKER_CONFIGURATION, objects, assembled, labels)
        image = DriverImage(
            code=assembled.read_bytes(),
            addresses=read_addresses(labels),
        )

    verify_addresses(image)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / DRIVER_CODE_NAME).write_bytes(image.code)
    return image


def assemble_sources(toolchain: Toolchain, work_directory: Path) -> List[Path]:
    """Assembles every source the driver is built from.

    Args:
        toolchain: The cc65 programs the build runs.
        work_directory: The directory receiving the object files.

    Returns:
        List[Path]: The object files, in the order they take in the image.

    Raises:
        DriverBuildError: If the assembler reports a failure.
    """
    objects: List[Path] = []
    for name in SOURCE_NAMES:
        object_file = (work_directory / name).with_suffix(OBJECT_SUFFIX)
        toolchain.assemble(SOURCE_DIRECTORY / name, INCLUDE_DIRECTORY, object_file)
        objects.append(object_file)

    return objects


def verify_addresses(image: DriverImage) -> None:
    """Holds a build's own layout to the addresses the driver is built to answer at.

    The exporter states those addresses without an assembler, so a build that laid the image out
    elsewhere would leave the committed driver and the header describing it telling different
    stories.

    Args:
        image: The assembled bytes and the addresses the linker reported for them.

    Raises:
        DriverBuildError: If any address departs from the one a driver of that length answers at.
    """
    expected = DriverAddresses.for_code(len(image.code))
    mismatches = [
        f"{name} at {reported:#06x} where the driver answers at {stated:#06x}"
        for name, reported, stated in (
            ("load", image.addresses.load, expected.load),
            ("init", image.addresses.init, expected.init),
            ("play", image.addresses.play, expected.play),
            ("song", image.addresses.song, expected.song),
        )
        if reported != stated
    ]

    if mismatches:
        raise DriverBuildError(f"the linker laid the driver out with {', '.join(mismatches)}")
