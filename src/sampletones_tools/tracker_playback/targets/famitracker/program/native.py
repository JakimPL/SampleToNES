import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import EXPORT_SWITCH


@dataclass(frozen=True)
class NativeProgram:
    """FamiTracker run directly, the way Windows runs it.

    FamiTracker reads an argument starting with ``/`` or ``-`` as a switch, so every path is given
    absolute: on Windows that opens with a drive letter.

    Attributes:
        executable: The FamiTracker program file.
    """

    executable: Path

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
        """
        return [
            str(self.executable.resolve()),
            str(module.resolve()),
            EXPORT_SWITCH,
            str(nsf.resolve()),
            str(log.resolve()),
        ]

    def environment(self) -> Dict[str, str]:
        """The environment the export runs in: the one the check runs in."""
        return dict(os.environ)
