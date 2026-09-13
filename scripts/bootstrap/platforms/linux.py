from pathlib import Path
from typing import Dict, Final, Mapping, Optional, Sequence, Tuple

from bootstrap.platforms.bundling import Bundling

LINUX: Final[str] = "Linux"
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
BUNDLING: Final[Bundling] = Bundling(
    icon=PNG_ICON,
    executable_suffix="",
    pyaudio_advice=(
        "Run 'make system-deps' to install the PortAudio packages, then 'make build' to reinstall the dependencies."
    ),
    tkinter_advice="Run 'make system-deps' to install python3-tk, then build again.",
    tkinter_warning=(
        "This bundle opens file dialogs through zenity or kdialog, which the machine running it has to "
        "provide. Run 'make system-deps' to install python3-tk and carry Tk as a self-contained fallback."
    ),
)


def posix_interpreter(environment: Path) -> Path:
    """The interpreter a POSIX virtual environment at ``environment`` runs."""
    return environment.joinpath(*POSIX_INTERPRETER)


class Linux:
    """A Debian-based Linux: packages through apt, a launcher without an extension."""

    @property
    def name(self) -> str:
        return LINUX

    @property
    def cuda(self) -> bool:
        return True

    def interpreter(self, environment: Path) -> Path:
        return posix_interpreter(environment)

    def bundling(self) -> Bundling:
        return BUNDLING

    def missing_package_manager(self) -> Optional[str]:
        return None

    def system_packages(self) -> Sequence[Sequence[str]]:
        return (
            ("sudo", "apt-get", "update"),
            ("sudo", "apt-get", "install", "-y", *SYSTEM_PACKAGES),
        )

    def setup_variables(self, base: Mapping[str, str], *, machine: str) -> Dict[str, str]:
        del machine
        return dict(base)

    def build_flags(self, *, machine: str) -> Sequence[str]:
        del machine
        return ()

    def nvidia_smi_locations(self, environment: Mapping[str, str]) -> Sequence[Path]:
        del environment
        return ()
