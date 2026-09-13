import argparse
import os
import platform as running
import sys
from typing import Dict, Final, List, Mapping, Optional, Sequence

import detect_cuda

from bootstrap.processes import expect_success, run
from bootstrap.repository import repository_root

GPU_AUTO: Final[str] = "auto"
GPU_OFF: Final[str] = "0"
DEFAULT_GPU: Final[str] = GPU_AUTO
DEVELOPMENT_GROUP: Final[str] = "dev"
DARWIN: Final[str] = "Darwin"
ARCHFLAGS: Final[str] = "ARCHFLAGS"


def gpu_extra(choice: str, *, system: str) -> Optional[str]:
    """The optional-dependency extra a GPU choice selects.

    Args:
        choice: ``auto`` to read the NVIDIA driver, ``0`` for the CPU backend, or an extra's name.
        system: The name ``platform.system()`` reports.

    Returns:
        Optional[str]: The extra, or ``None`` for the CPU backend.
    """
    if choice == GPU_OFF:
        return None

    if choice == GPU_AUTO:
        detection = detect_cuda.detect(system=system)
        print(detection.reason, file=sys.stderr)
        return detection.extra

    return choice


def setup_commands(extra: Optional[str]) -> List[List[str]]:
    """The commands that create the development environment and install the global command.

    Args:
        extra: The GPU extra installed with the package, or ``None`` for the CPU backend.

    Returns:
        List[List[str]]: The commands, in order.
    """
    synchronize = ["uv", "sync", "--group", DEVELOPMENT_GROUP]
    package = "."
    if extra is not None:
        synchronize.extend(("--extra", extra))
        package = f".[{extra}]"

    return [
        synchronize,
        ["uv", "tool", "install", "--force", package],
    ]


def setup_environment_variables(
    base: Mapping[str, str],
    *,
    system: str,
    machine: str,
) -> Dict[str, str]:
    """The variables the setup commands see: the caller's, pinned to the native architecture on macOS.

    Homebrew's PortAudio carries the machine's own architecture while a python.org interpreter
    compiles for both, so the flag settles audio playback on the native one.
    """
    variables = dict(base)
    if system == DARWIN:
        variables[ARCHFLAGS] = f"-arch {machine}"

    return variables


def main(argv: Sequence[str]) -> int:
    """Creates the development environment and installs the global ``sampletones`` command."""
    parser = argparse.ArgumentParser(description="Set up the SampleToNES development environment.")
    parser.add_argument(
        "--gpu",
        default=DEFAULT_GPU,
        help="auto to match the NVIDIA driver, 0 for the CPU backend, or the name of a GPU extra",
    )
    arguments = parser.parse_args(list(argv))

    root = repository_root()
    system = running.system()
    environment = setup_environment_variables(os.environ, system=system, machine=running.machine())
    for command in setup_commands(gpu_extra(arguments.gpu, system=system)):
        expect_success(run, command, cwd=root, environment=environment)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
