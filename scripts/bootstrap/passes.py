from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Sequence, Tuple

from bootstrap.processes import Runner


@dataclass(frozen=True)
class Pass:
    """One named command a script announces and runs from the repository root.

    Attributes:
        name: What the step is called in the report and on the command line.
        announcement: The line printed as the step starts.
        command: The program and its arguments, run from the repository root.
    """

    name: str
    announcement: str
    command: Tuple[str, ...]


def run_pass(
    current: Pass,
    *,
    root: Path,
    runner: Runner,
    environment: Mapping[str, str],
) -> int:
    """Announces one pass and runs its command from the repository.

    Args:
        current: The pass.
        root: The repository, which the command runs in.
        runner: What runs the command.
        environment: The variables the command sees.

    Returns:
        int: The status the command exited with.
    """
    print(current.announcement)
    return runner(current.command, cwd=root, environment=environment, quiet=False)


def run_passes(
    passes: Sequence[Pass],
    *,
    root: Path,
    runner: Runner,
    environment: Mapping[str, str],
) -> List[str]:
    """Runs every pass in order and names the ones that failed.

    Every pass runs whatever the earlier ones reported, so one run shows everything that is
    wrong.

    Args:
        passes: The steps, in order.
        root: The repository, which every command runs in.
        runner: What runs the commands.
        environment: The variables the commands see.

    Returns:
        List[str]: The names of the passes that exited with a failure, in order.
    """
    failed: List[str] = []
    for current in passes:
        if run_pass(current, root=root, runner=runner, environment=environment) != 0:
            failed.append(current.name)

    return failed
