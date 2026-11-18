from typing import Dict, Tuple

from sampletones_core.exports.format import ExportFormat
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.backend import ProgramBackend
from sampletones_player.export.container import ProgramContainer
from sampletones_player.export.containers.nsf import NSFContainer


def program_backends() -> Dict[ExportFormat, ProgramBackend]:
    """Every backend writing a console program, keyed by the format its container writes.

    The driver every file carries is read here once and handed to each container, so every kind
    of file plays a song through the same assembled bytes, and a build shipping without them
    reports itself where the backends are composed.

    Returns:
        Dict[ExportFormat, ProgramBackend]: The backends, each writing a request as its own
        source states it.

    Raises:
        OSError: If the packaged driver is absent.
        ValueError: If the packaged driver lays out something other than the addresses it is
            built to answer at.
    """
    driver = DriverImage.load()
    containers: Tuple[ProgramContainer, ...] = (NSFContainer(driver),)
    return {container.export_format: ProgramBackend.stated(container) for container in containers}
