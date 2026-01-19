from __future__ import annotations

import platform
from enum import StrEnum


class System(StrEnum):
    """
    String enumeration for system-related constants.

    Supports Windows, Linux, and MacOS.
    """

    WINDOWS = "Windows"
    LINUX = "Linux"
    MACOS = "MacOS"

    @classmethod
    def current(cls) -> System:
        """
        Returns the current operating system as a System enum member.

        Returns:
            System: The current operating system.

        Raises:
            OSError: If the operating system is unsupported.
        """
        system_name = platform.system()
        match system_name:
            case "Windows":
                return cls.WINDOWS
            case "Linux":
                return cls.LINUX
            case "Darwin":
                return cls.MACOS

        raise OSError(f"Unsupported operating system: {system_name}")
