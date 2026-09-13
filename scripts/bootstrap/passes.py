from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Sequence, Tuple

from bootstrap.processes import Runner


@dataclass(frozen=True)
class Pass:
    """One step of a run that reports every failure at once: named, announced, run as one command.

    Attributes:
        name: What the step is called in the report and on the command line.
        announcement: The line printed as the step starts.
        command: The program and its arguments, run from the repository root.
    """

    name: str
    announcement: str
    command: Tuple[str, ...]


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
        print(current.announcement)
        status = runner(current.command, cwd=root, environment=environment, quiet=False)
        if status != 0:
            failed.append(current.name)

    return failed
