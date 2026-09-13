from pathlib import Path
from typing import Final, Optional, Sequence, Tuple

LINUX: Final[str] = "Linux"
POSIX_LAUNCHER: Final[str] = "sampletones"
POSIX_INTERPRETER: Final[Tuple[str, str]] = ("bin", "python")
PNG_ICON: Final[str] = "src/sampletones_assets/icons/sampletones.png"
SYSTEM_PACKAGES: Final[Tuple[str, ...]] = (
    "libportaudio2",
    "libasound-dev",
    "libpulse-dev",
    "portaudio19-dev",
    "python3-tk",
    "tk-dev",
    "tcl-dev",
    "libgl1",
    "libegl1",
    "libx11-6",
    "libx11-xcb1",
    "libxcursor1",
    "libxi6",
    "libxinerama1",
    "libxrandr2",
    "libxrender1",
    "libxxf86vm1",
)


def posix_interpreter(environment: Path) -> Path:
    """The interpreter a POSIX virtual environment at ``environment`` runs."""
    return environment.joinpath(*POSIX_INTERPRETER)


def posix_launcher(distribution: Path, *, release: bool) -> Path:
    """The executable PyInstaller writes under ``distribution`` on a POSIX system."""
    if release:
        return distribution / POSIX_LAUNCHER / POSIX_LAUNCHER

    return distribution / POSIX_LAUNCHER


class Linux:
    """A Debian-based Linux: packages through apt, a launcher without an extension."""

    @property
    def name(self) -> str:
        return LINUX

    @property
    def bundles(self) -> bool:
        return True

    @property
    def icon(self) -> str:
        return PNG_ICON

    @property
    def pyaudio_advice(self) -> str:
        return (
            "Run 'make system-deps' to install the PortAudio packages, then 'make build' to reinstall the dependencies."
        )

    @property
    def tkinter_advice(self) -> str:
        return "Run 'make system-deps' to install python3-tk, then build again."

    @property
    def tkinter_warning(self) -> str:
        return (
            "This bundle opens file dialogs through zenity or kdialog, which the machine running it has to "
            "provide. Run 'make system-deps' to install python3-tk and carry Tk as a self-contained fallback."
        )

    def interpreter(self, environment: Path) -> Path:
        return posix_interpreter(environment)

    def launcher(self, distribution: Path, *, release: bool) -> Path:
        return posix_launcher(distribution, release=release)

    def missing_package_manager(self) -> Optional[str]:
        return None

    def system_packages(self) -> Sequence[Sequence[str]]:
        return (
            ("sudo", "apt-get", "update"),
            ("sudo", "apt-get", "install", "-y", *SYSTEM_PACKAGES),
        )

    def build_environment(self, *, machine: str, portaudio_prefix: str) -> Sequence[str]:
        del machine, portaudio_prefix
        return ()
