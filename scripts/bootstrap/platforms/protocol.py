from pathlib import Path
from typing import Optional, Protocol, Sequence


class Platform(Protocol):
    """What building and running SampleToNES has to know about the system it happens on."""

    @property
    def name(self) -> str:
        """The name ``platform.system()`` reports for the system."""

    @property
    def bundles(self) -> bool:
        """Whether a standalone bundle is built on the system."""

    @property
    def icon(self) -> str:
        """The icon file a bundle is stamped with, relative to the repository."""

    @property
    def pyaudio_advice(self) -> str:
        """How to supply PortAudio to the build interpreter."""

    @property
    def tkinter_advice(self) -> str:
        """How to supply Tk to the build interpreter for a release bundle."""

    @property
    def tkinter_warning(self) -> str:
        """What a development bundle built without Tk does about file dialogs."""

    def interpreter(self, environment: Path) -> Path:
        """The interpreter a virtual environment at ``environment`` runs.

        Args:
            environment: The virtual environment's directory.

        Returns:
            Path: The interpreter.
        """

    def launcher(self, distribution: Path, *, release: bool) -> Path:
        """The executable PyInstaller writes under ``distribution``.

        Args:
            distribution: The directory the bundle is written into.
            release: Whether the bundle is a release, which is a directory beside its launcher.

        Returns:
            Path: The launcher.
        """

    def missing_package_manager(self) -> Optional[str]:
        """What stands in the way of installing system packages, or ``None`` where nothing does."""

    def system_packages(self) -> Sequence[Sequence[str]]:
        """The commands that install the system packages the application needs, in order."""

    def build_environment(self, *, machine: str, portaudio_prefix: str) -> Sequence[str]:
        """The ``KEY=VALUE`` lines a build exports so audio playback compiles against PortAudio.

        Args:
            machine: The processor architecture ``platform.machine()`` reports.
            portaudio_prefix: Where the package manager installed PortAudio, or empty where the
                system carries it without one.

        Returns:
            Sequence[str]: The lines, empty where the build needs none.
        """
