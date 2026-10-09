import platform
from typing import Dict, Final

from bootstrap.platforms.linux import LINUX, Linux
from bootstrap.platforms.macos import DARWIN, MacOS
from bootstrap.platforms.protocol import Platform
from bootstrap.platforms.windows import WINDOWS, Windows

PLATFORMS: Final[Dict[str, Platform]] = {
    LINUX: Linux(),
    WINDOWS: Windows(),
    DARWIN: MacOS(),
}


def platform_named(system: str) -> Platform:
    """The platform a system name selects.

    Args:
        system: The name ``platform.system()`` reports.

    Returns:
        Platform: The platform.

    Raises:
        SystemExit: If SampleToNES supports no system of that name.
    """
    chosen = PLATFORMS.get(system)
    if chosen is None:
        raise SystemExit(f"ERROR: {system} is not a system SampleToNES builds on; supported: {', '.join(PLATFORMS)}.")

    return chosen


def current_platform() -> Platform:
    """The platform the script runs on."""
    return platform_named(platform.system())
