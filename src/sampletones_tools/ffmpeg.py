from typing import Dict, Final, Tuple

from sampletones_shared.utils.system.programs import missing_program_message
from sampletones_shared.utils.system.system import System

FFMPEG: Final[str] = "ffmpeg"
UNATTENDED: Final[Tuple[str, ...]] = ("-nostdin", "-y")

INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install ffmpeg",
    System.MACOS: "brew install ffmpeg",
    System.WINDOWS: "install ffmpeg from https://ffmpeg.org and add its bin directory to PATH",
}


def missing_ffmpeg_message(purpose: str) -> str:
    """What a tool reports when ffmpeg is absent: what it runs ffmpeg for and how this system installs it.

    Every tool that runs ffmpeg names the program and its install command the same way, and raises the
    error of its own kind with this message.

    Raises:
        OSError: If the system is unsupported.
    """
    return missing_program_message(FFMPEG, purpose, INSTALL_HINTS)
