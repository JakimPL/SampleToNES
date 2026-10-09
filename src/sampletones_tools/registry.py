from typing import Final, Tuple

from sampletones_shared.command import Command
from sampletones_tools.calibration.command import CALIBRATION
from sampletones_tools.checks.command import CHECK
from sampletones_tools.codec.command import CODEC
from sampletones_tools.compatibility.command import COMPATIBILITY
from sampletones_tools.player.command import DRIVER
from sampletones_tools.samples.commands.btp import BTP
from sampletones_tools.samples.commands.ftm import FTM
from sampletones_tools.samples.commands.nsf import NSF
from sampletones_tools.tracker_playback.command import TRACKER_PLAYBACK

DEVELOPER_COMMANDS: Final[Tuple[Command, ...]] = (
    BTP,
    CALIBRATION,
    CHECK,
    CODEC,
    COMPATIBILITY,
    DRIVER,
    FTM,
    NSF,
    TRACKER_PLAYBACK,
)
