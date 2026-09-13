import shlex
import subprocess
from pathlib import Path
from typing import Mapping, Protocol, Sequence


class Runner(Protocol):
    """Runs a command to completion and answers with its exit status."""

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str],
        quiet: bool,
    ) -> int: ...


def run(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    quiet: bool,
) -> int:
    """Runs a command in ``cwd`` under ``environment`` and answers with its exit status.

    A quiet run keeps the command's output to itself, which is what a probe asks for.

    Args:
        command: The program and its arguments.
        cwd: The directory the command runs in.
        environment: The variables the command sees.
        quiet: Whether the command's output is captured instead of shown.

    Returns:
        int: The command's exit status.
    """
    completed = subprocess.run(
        list(command),
        cwd=str(cwd),
        env=dict(environment),
        check=False,
        capture_output=quiet,
    )
    return completed.returncode


def expect_success(
    runner: Runner,
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    """Runs a command the operation depends on.

    Args:
        runner: What runs the command.
        command: The program and its arguments.
        cwd: The directory the command runs in.
        environment: The variables the command sees.

    Raises:
        SystemExit: If the command exits with a status other than zero.
    """
    status = runner(command, cwd=cwd, environment=environment, quiet=False)
    if status != 0:
        raise SystemExit(f"ERROR: {shlex.join(command)} exited with status {status}")
