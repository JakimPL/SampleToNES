from pathlib import Path
from typing import Final, Optional, Sequence

from bootstrap.platforms.linux import PNG_ICON, posix_interpreter, posix_launcher

DARWIN: Final[str] = "Darwin"
HOMEBREW: Final[str] = "brew"
HOMEBREW_SITE: Final[str] = "https://brew.sh"
PORTAUDIO: Final[str] = "portaudio"


class MacOS:
    """macOS: PortAudio through Homebrew, and the application run from source."""

    @property
    def name(self) -> str:
        return DARWIN

    @property
    def bundles(self) -> bool:
        return False

    @property
    def icon(self) -> str:
        return PNG_ICON

    @property
    def pyaudio_advice(self) -> str:
        return "Run 'make system-deps' to install PortAudio through Homebrew."

    @property
    def tkinter_advice(self) -> str:
        return "Install Python from python.org, which includes Tk."

    @property
    def tkinter_warning(self) -> str:
        return "This bundle opens no file dialogs. Install Python from python.org to include Tk."

    def interpreter(self, environment: Path) -> Path:
        return posix_interpreter(environment)

    def launcher(self, distribution: Path, *, release: bool) -> Path:
        return posix_launcher(distribution, release=release)

    def missing_package_manager(self) -> Optional[str]:
        return (
            "ERROR: Homebrew is required to install the macOS system dependencies.\n"
            f"Install it from {HOMEBREW_SITE}, then run this script again."
        )

    def system_packages(self) -> Sequence[Sequence[str]]:
        return ((HOMEBREW, "install", PORTAUDIO),)

    def build_environment(self, *, machine: str, portaudio_prefix: str) -> Sequence[str]:
        """The flags compiling audio playback against Homebrew's PortAudio on the native architecture.

        Raises:
            SystemExit: If Homebrew reported no PortAudio prefix.
        """
        if not portaudio_prefix:
            raise SystemExit(
                "ERROR: Homebrew is required to locate the PortAudio headers and library.\n"
                "Run 'make system-deps' first."
            )

        return (
            f"CFLAGS=-I{portaudio_prefix}/include",
            f"LDFLAGS=-L{portaudio_prefix}/lib",
            f"ARCHFLAGS=-arch {machine}",
        )
