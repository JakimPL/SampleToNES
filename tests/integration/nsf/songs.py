from typing import Final

from sampletones_core.project.project import Project
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.nsf import PROGRAM_SIZE

RECORD_BYTES_PER_TICK: Final[int] = 11


def available_bytes(driver_image: DriverImage) -> int:
    """The program area the song block is written into, behind the driver."""
    return PROGRAM_SIZE - len(driver_image.code)


def lengthened(project: Project, frames: int) -> Project:
    """``project`` with its order repeated to ``frames`` positions, over the same samples.

    The song is copied rather than edited so the session's own project keeps the arrangement
    every other case reads.
    """
    longer = Project.create(
        rows_per_pattern=project.song.rows_per_pattern,
        settings=project.settings,
    )
    for sample in project.samples:
        longer.samples.append(sample)

    longer.song = project.song.model_copy(deep=True)
    while longer.song.order_length() < frames:
        longer.song.duplicate_frame(longer.song.order_length() - 1)

    return longer
