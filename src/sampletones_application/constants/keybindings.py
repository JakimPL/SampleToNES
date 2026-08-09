from typing import Dict, Final

from sampletones_shared.utils.system.system import System

DEFAULT_SCHEME_NAME: Final[str] = "default"
MACOS_SCHEME_NAME: Final[str] = "macos"

PLATFORM_SCHEME_NAMES: Final[Dict[System, str]] = {
    System.LINUX: DEFAULT_SCHEME_NAME,
    System.WINDOWS: DEFAULT_SCHEME_NAME,
    System.MACOS: MACOS_SCHEME_NAME,
}


def platform_scheme_name() -> str:
    """The scheme a fresh profile starts on, which is the keyboard the platform is worked at.

    A Mac carries Command where the other two carry Control, so the keys a reader already knows
    from every other application on their machine are the keys the build opens with. A stored
    preference is read ahead of this, so a reader who chose another scheme keeps it.

    Returns:
        str: The name of the scheme the current platform ships.
    """
    return PLATFORM_SCHEME_NAMES[System.current()]
