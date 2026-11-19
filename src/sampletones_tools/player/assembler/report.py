from typing import List

from sampletones_player.driver.image import DriverImage
from sampletones_player.shell.image import ShellImage
from sampletones_player.specification.driver import DRIVER_CODE_NAME
from sampletones_player.specification.shell import SHELL_CODE_NAME


def layout_lines(image: DriverImage) -> List[str]:
    """The layout a build produced, one line per figure a reader checks against the header."""
    addresses = image.addresses
    return [
        f"{DRIVER_CODE_NAME}  {len(image.code)} bytes, ${addresses.load:04X}-${addresses.song - 1:04X}",
        f"init        ${addresses.init:04X}",
        f"play        ${addresses.play:04X}",
        f"song        ${addresses.song:04X}",
    ]


def shell_lines(shell: ShellImage) -> List[str]:
    """The shell a build produced: its length and where it starts, and the routines the console enters."""
    frame, power_on, interrupt = shell.vectors
    return [
        f"{SHELL_CODE_NAME}   {len(shell.code)} bytes, ${shell.start:04X}-$FFFF",
        f"reset       ${power_on:04X}",
        f"frame       ${frame:04X}",
        f"interrupt   ${interrupt:04X}",
    ]
