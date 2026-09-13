import argparse
import os
import platform as running
import sys
from pathlib import Path
from typing import Final, List, Mapping, Optional, Sequence, Tuple

from bootstrap.cuda import detect
from bootstrap.layout import repository_root
from bootstrap.platforms.factory import current_platform
from bootstrap.platforms.protocol import Platform
from bootstrap.processes import Runner, expect_success, run
from bootstrap.project import DEVELOPMENT_GROUP, GPU_CUDA11_EXTRA, GPU_EXTRA, read_project

GPU_AUTO: Final[str] = "auto"
GPU_OFF: Final[str] = "0"
GPU_CHOICES: Final[Tuple[str, ...]] = (
    GPU_AUTO,
    GPU_OFF,
    GPU_EXTRA,
    GPU_CUDA11_EXTRA,
)
DEFAULT_GPU: Final[str] = GPU_AUTO


def gpu_extra(
    choice: str,
    platform: Platform,
    environment: Mapping[str, str],
) -> Optional[str]:
    """The optional-dependency extra a GPU choice selects.

    Args:
        choice: ``auto`` to read the NVIDIA driver, ``0`` for the CPU backend, or an extra's name.
        platform: The system the setup runs on.
        environment: The variables the driver's locations are read from.

    Returns:
        Optional[str]: The extra, or ``None`` for the CPU backend.
    """
    if choice == GPU_OFF:
        return None

    if choice == GPU_AUTO:
        detection = detect(platform, environment)
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


def set_up_environment(
    root: Path,
    platform: Platform,
    extra: Optional[str],
    *,
    machine: str,
    runner: Runner,
    environment: Mapping[str, str],
) -> None:
    """Synchronizes the development environment and installs the global ``sampletones`` command.

    Args:
        root: The repository.
        platform: The system the setup runs on, which adds the variables the build needs.
        extra: The GPU extra installed with the package, or ``None`` for the CPU backend.
        machine: The processor architecture ``platform.machine()`` reports.
        runner: What runs the commands.
        environment: The caller's variables.

    Raises:
        SystemExit: If a command fails.
    """
    variables = platform.setup_variables(environment, machine=machine)
    for command in setup_commands(extra):
        expect_success(runner, command, cwd=root, environment=variables)


def main(argv: Sequence[str]) -> int:
    """Creates the development environment and installs the global ``sampletones`` command."""
    parser = argparse.ArgumentParser(description="Set up the SampleToNES development environment.")
    parser.add_argument(
        "--gpu",
        default=DEFAULT_GPU,
        choices=GPU_CHOICES,
        help="auto to match the NVIDIA driver, 0 for the CPU backend, or the GPU extra to install",
    )
    arguments = parser.parse_args(list(argv))

    root = repository_root()
    read_project(root)
    platform = current_platform()
    set_up_environment(
        root,
        platform,
        gpu_extra(arguments.gpu, platform, os.environ),
        machine=running.machine(),
        runner=run,
        environment=os.environ,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
