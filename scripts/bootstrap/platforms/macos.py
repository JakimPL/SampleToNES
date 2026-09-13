import shutil
import subprocess
from pathlib import Path
from typing import Dict, Final, Mapping, Optional, Sequence

from bootstrap.platforms.bundling import Bundling
from bootstrap.platforms.linux import posix_interpreter

DARWIN: Final[str] = "Darwin"
HOMEBREW: Final[str] = "brew"
HOMEBREW_SITE: Final[str] = "https://brew.sh"
PORTAUDIO: Final[str] = "portaudio"
ARCHFLAGS: Final[str] = "ARCHFLAGS"
NO_BUNDLE: Final[str] = (
    "ERROR: a standalone bundle is built on Linux and Windows.\n"
    "On macOS, SampleToNES runs from source:\n"
    "\n"
    "    make system-deps\n"
    "    make setup\n"
    "    make run\n"
    "\n"
    "See docs/guide/installation.md for the full steps."
)


def homebrew_prefix(package: str) -> str:
    """Where Homebrew installed ``package``, or empty where Homebrew or the package is absent."""
    if shutil.which(HOMEBREW) is None:
        return ""

    completed = subprocess.run(
        [HOMEBREW, "--prefix", package],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""

    return completed.stdout.strip()


def architecture_flag(machine: str) -> str:
    """The flag compiling an extension for the machine's own architecture alone."""
    return f"-arch {machine}"


class MacOS:
    """macOS: PortAudio through Homebrew, and the application run from source.

    Homebrew's PortAudio carries the machine's own architecture while a python.org interpreter
    compiles for both, so the setup and a build pin ``ARCHFLAGS`` to the native one. NVIDIA CUDA
    has no driver on the system, so the CPU backend is the one it runs.
    """

    @property
    def name(self) -> str:
        return DARWIN

    @property
    def cuda(self) -> bool:
        return False

    def interpreter(self, environment: Path) -> Path:
        return posix_interpreter(environment)

    def bundling(self) -> Bundling:
        raise SystemExit(NO_BUNDLE)

    def missing_package_manager(self) -> Optional[str]:
        if shutil.which(HOMEBREW) is not None:
            return None

        return (
            "ERROR: Homebrew is required to install the macOS system dependencies.\n"
            f"Install it from {HOMEBREW_SITE}, then run this script again."
        )

    def system_packages(self) -> Sequence[Sequence[str]]:
        return ((HOMEBREW, "install", PORTAUDIO),)

    def setup_variables(self, base: Mapping[str, str], *, machine: str) -> Dict[str, str]:
        return {**base, ARCHFLAGS: architecture_flag(machine)}

    def build_flags(self, *, machine: str) -> Sequence[str]:
        """The flags compiling audio playback against Homebrew's PortAudio on the native architecture.

        Raises:
            SystemExit: If Homebrew reports no PortAudio prefix.
        """
        prefix = homebrew_prefix(PORTAUDIO)
        if not prefix:
            raise SystemExit(
                "ERROR: Homebrew is required to locate the PortAudio headers and library.\n"
                "Run 'make system-deps' first."
            )

        return (
            f"CFLAGS=-I{prefix}/include",
            f"LDFLAGS=-L{prefix}/lib",
            f"{ARCHFLAGS}={architecture_flag(machine)}",
        )

    def nvidia_smi_locations(self, environment: Mapping[str, str]) -> Sequence[Path]:
        del environment
        return ()
