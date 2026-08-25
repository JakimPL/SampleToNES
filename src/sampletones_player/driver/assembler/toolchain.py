from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Sequence

from sampletones_shared.exceptions import DriverBuildError, ToolchainMissingError
from sampletones_shared.utils.system.programs import (
    locate_program,
    missing_program_message,
)
from sampletones_shared.utils.system.system import System

ASSEMBLER: Final[str] = "ca65"
LINKER: Final[str] = "ld65"
TARGET_CPU: Final[str] = "6502"
ASSEMBLY_PURPOSE: Final[str] = "the player driver is assembled with cc65"

INSTALL_HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install cc65",
    System.MACOS: "brew install cc65",
    System.WINDOWS: "install cc65 from https://cc65.github.io and add its bin directory to PATH",
}


@dataclass(frozen=True)
class Toolchain:
    """The cc65 programs a driver build runs.

    Locating both programs up front is what lets a build fail with an install hint before it
    writes anything, and holding them as paths keeps every later call pointed at the same pair.

    Attributes:
        assembler: The ``ca65`` program, which turns one assembly source into an object file.
        linker: The ``ld65`` program, which lays the object files out into the driver image.
    """

    assembler: Path
    linker: Path

    @classmethod
    def locate(cls) -> Toolchain:
        """The cc65 programs installed on this system.

        Returns:
            Toolchain: The assembler and the linker, each resolved to its path.

        Raises:
            ToolchainMissingError: If either program is absent, naming the way this system
                installs cc65.
        """
        return cls(assembler=cls.find(ASSEMBLER), linker=cls.find(LINKER))

    @staticmethod
    def find(program: str) -> Path:
        """Resolves one cc65 program to its path.

        Args:
            program: The program's name, as it answers on the command line.

        Returns:
            Path: Where the program is installed.

        Raises:
            ToolchainMissingError: If the program is absent from the system.
        """
        located = locate_program(program)
        if located is None:
            raise ToolchainMissingError(missing_program_message(program, ASSEMBLY_PURPOSE, INSTALL_HINTS))

        return located

    def assemble(self, source: Path, include_directory: Path, destination: Path) -> None:
        """Assembles one 6502 source into an object file.

        Args:
            source: The assembly source to translate.
            include_directory: Where the sources' ``.include`` files are found.
            destination: The object file the assembler writes.

        Raises:
            DriverBuildError: If the assembler reports a failure.
        """
        self.run(
            [
                str(self.assembler),
                "--cpu",
                TARGET_CPU,
                "--include-dir",
                str(include_directory),
                "-o",
                str(destination),
                str(source),
            ],
        )

    def link(
        self,
        configuration: Path,
        objects: Sequence[Path],
        destination: Path,
        labels: Path,
    ) -> None:
        """Lays the object files out into the driver image.

        The line names our own configuration and our own object files alone, which is what keeps
        the image entirely ours to ship: reaching for a cc65 target or library would place that
        project's start-up code and routines in the bytes the package commits.

        Args:
            configuration: The linker configuration stating the memory layout.
            objects: The object files, in the order they take in the image.
            destination: The driver image the linker writes.
            labels: The label file the linker writes, holding each symbol's address.

        Raises:
            DriverBuildError: If the linker reports a failure.
        """
        self.run(
            [
                str(self.linker),
                "--config",
                str(configuration),
                "-Ln",
                str(labels),
                "-o",
                str(destination),
                *[str(object_file) for object_file in objects],
            ],
        )

    @staticmethod
    def run(command: Sequence[str]) -> None:
        """Runs one cc65 program and answers for what it reported.

        Args:
            command: The program and its arguments.

        Raises:
            DriverBuildError: If the program exits with a failure, carrying what it printed.
        """
        arguments: List[str] = list(command)
        completed = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise DriverBuildError(f"{Path(arguments[0]).name} failed: {completed.stderr.strip()}")
