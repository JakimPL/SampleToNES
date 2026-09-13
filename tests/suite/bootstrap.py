from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class RecordedCommand:
    """One command a recording runner was asked to run.

    Attributes:
        command: The program and its arguments.
        cwd: The directory it was to run in.
        environment: The variables it was to see.
        quiet: Whether its output was to be captured.
    """

    command: Tuple[str, ...]
    cwd: Path
    environment: Dict[str, str]
    quiet: bool

    @property
    def line(self) -> str:
        """The command as one line."""
        return " ".join(self.command)


class RecordingRunner:
    """A runner that records every command and answers with the status a test assigned it.

    A status is assigned by a fragment of the command line, so a probe such as ``import pyaudio``
    can be made to fail while everything else succeeds. A callback runs on every command, which
    lets a test leave behind the files a real command would have written.
    """

    def __init__(
        self,
        statuses: Mapping[str, int],
        on_run: Optional[Callable[[Sequence[str]], None]],
    ) -> None:
        self.commands: List[RecordedCommand] = []
        self._statuses = dict(statuses)
        self._on_run = on_run

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str],
        quiet: bool,
    ) -> int:
        recorded = RecordedCommand(
            command=tuple(command),
            cwd=cwd,
            environment=dict(environment),
            quiet=quiet,
        )
        self.commands.append(recorded)
        if self._on_run is not None:
            self._on_run(command)

        for fragment, status in self._statuses.items():
            if fragment in recorded.line:
                return status

        return 0

    @property
    def lines(self) -> List[str]:
        """Every recorded command as one line, in the order run."""
        return [recorded.line for recorded in self.commands]
