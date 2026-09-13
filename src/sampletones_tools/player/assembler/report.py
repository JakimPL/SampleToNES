from typing import List

from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.driver import DRIVER_CODE_NAME


def layout_lines(image: DriverImage) -> List[str]:
    """The layout a build produced, one line per figure a reader checks against the header."""
    addresses = image.addresses
    return [
        f"{DRIVER_CODE_NAME}  {len(image.code)} bytes, ${addresses.load:04X}-${addresses.song - 1:04X}",
        f"init        ${addresses.init:04X}",
        f"play        ${addresses.play:04X}",
        f"song        ${addresses.song:04X}",
    ]
