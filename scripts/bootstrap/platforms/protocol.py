from pathlib import Path
from typing import Dict, Mapping, Optional, Protocol, Sequence

from bootstrap.platforms.bundling import Bundling


class Platform(Protocol):
    """What building and running SampleToNES has to know about the system it happens on."""

    @property
    def name(self) -> str:
        """The name ``platform.system()`` reports for the system."""

    @property
    def cpu_backend_reason(self) -> Optional[str]:
        """Why the system runs the CPU backend whatever its hardware, or ``None`` where CUDA can run."""

    def interpreter(self, environment: Path) -> Path:
        """The interpreter a virtual environment at ``environment`` runs.

        Args:
            environment: The virtual environment's directory.

        Returns:
            Path: The interpreter.
        """

    def bundling(self) -> Bundling:
        """What building a standalone bundle takes on the system.

        Returns:
            Bundling: The icon, the launcher's name and the advice a build gives.

        Raises:
            SystemExit: If the system builds no bundle, naming how SampleToNES runs there.
        """

    def missing_package_manager(self) -> Optional[str]:
        """What stands in the way of installing system packages, or ``None`` where nothing does."""

    def system_packages(self) -> Sequence[Sequence[str]]:
        """The commands that install the system packages the application needs, in order."""

    def setup_variables(self, base: Mapping[str, str], *, machine: str) -> Dict[str, str]:
        """The variables the development setup runs under: ``base`` and what the system adds to it.

        Args:
            base: The caller's variables.
            machine: The processor architecture ``platform.machine()`` reports.

        Returns:
            Dict[str, str]: The variables.
        """

    def build_flags(self, *, machine: str) -> Sequence[str]:
        """The ``KEY=VALUE`` lines a build exports so audio playback compiles against PortAudio.

        Args:
            machine: The processor architecture ``platform.machine()`` reports.

        Returns:
            Sequence[str]: The lines, empty where the build needs none.
        """

    def nvidia_smi_locations(self, environment: Mapping[str, str]) -> Sequence[Path]:
        """Where the NVIDIA driver installs ``nvidia-smi`` outside ``PATH``.

        Args:
            environment: The variables the locations are read from.

        Returns:
            Sequence[Path]: The candidates, in the order they are tried.
        """
