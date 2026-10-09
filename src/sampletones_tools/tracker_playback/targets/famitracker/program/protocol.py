from pathlib import Path
from typing import Dict, Final, List, Protocol

EXPORT_SWITCH: Final[str] = "-export"


class FamiTrackerProgram(Protocol):
    """FamiTracker as this system runs it, so its command-line export turns a module into an NSF.

    FamiTracker exports from its command line, ``FamiTracker.exe <module> -export <nsf> <log>``,
    writes what it did to the log and quits with no window shown. Each system reaches the Windows
    program its own way, and each way is one implementation.
    """

    @property
    def executable(self) -> Path:
        """The FamiTracker program file."""

    def export_command(
        self,
        module: Path,
        nsf: Path,
        log: Path,
    ) -> List[str]:
        """The command that exports a module to an NSF and writes FamiTracker's log.

        Args:
            module: The `.ftm` module to export.
            nsf: Where the NSF is written.
            log: Where FamiTracker writes what it did.

        Returns:
            List[str]: The program and its arguments.

        Raises:
            FamiTrackerError: If the paths cannot be put in the form FamiTracker reads.
        """

    def environment(self) -> Dict[str, str]:
        """The environment the export runs in."""
