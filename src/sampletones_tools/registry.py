from typing import Final, Tuple

from sampletones_shared.command import Command
from sampletones_tools.calibration.command import CALIBRATION

DEVELOPER_COMMANDS: Final[Tuple[Command, ...]] = (CALIBRATION,)
