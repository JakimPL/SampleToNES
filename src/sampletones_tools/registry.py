from typing import Final, Tuple

from sampletones_shared.command import Command
from sampletones_tools.assets.command import ICONS
from sampletones_tools.calibration.command import CALIBRATION
from sampletones_tools.player.command import DRIVER
from sampletones_tools.samples.command import NSF

DEVELOPER_COMMANDS: Final[Tuple[Command, ...]] = (CALIBRATION, DRIVER, ICONS, NSF)
