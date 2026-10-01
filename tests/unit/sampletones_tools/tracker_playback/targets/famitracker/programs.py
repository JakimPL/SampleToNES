import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Optional, Tuple

from sampletones_player.specification.nsf import PROGRAM_START
from sampletones_player.specification.registers import DMC_DIRECT_LOAD
from tests.unit.sampletones_tools.console.files import (
    INIT,
    PLAY,
    RETURN,
    STORE_ACCUMULATOR,
    NSFFile,
    absolute,
)

LOG_TEXT: Final[str] = "Opened the module.\nNSF export complete."
COUNTER: Final[int] = 0x00
LOAD_ZERO_PAGE: Final[int] = 0xA5
INCREMENT_ZERO_PAGE: Final[int] = 0xE6
EXPORT_SCRIPT: Final[str] = """
import shutil, sys
source, nsf, log, log_text = sys.argv[1:]
if source:
    shutil.copyfile(source, nsf)
with open(log, "w", encoding="utf-8") as stream:
    stream.write(log_text)
"""
MARKING_PLAY: Final[Tuple[int, ...]] = (
    LOAD_ZERO_PAGE,
    COUNTER,
    STORE_ACCUMULATOR,
    *absolute(DMC_DIRECT_LOAD),
    INCREMENT_ZERO_PAGE,
    COUNTER,
    RETURN,
)


def marking_nsf() -> bytes:
    """An NSF whose every play call starts a row: it writes a marker carrying how many calls came before."""
    return NSFFile(program={INIT - PROGRAM_START: (RETURN,), PLAY - PROGRAM_START: MARKING_PLAY}).data


@dataclass(frozen=True)
class StandInProgram:
    """A program standing in for FamiTracker: its export copies a prepared NSF into place and writes a log.

    It records every module it is asked to export, so a case reads what reached it.

    Attributes:
        executable: The program file the report names.
        source: The NSF the export leaves, or ``None`` for an export that writes none.
        exported: The modules the export was asked for, in order.
    """

    executable: Path
    source: Optional[Path]
    exported: List[bytes]

    def export_command(
        self,
        module: Path,
        nsf: Path,
        log: Path,
    ) -> List[str]:
        self.exported.append(module.read_bytes())
        source = str(self.source) if self.source is not None else ""
        return [sys.executable, "-c", EXPORT_SCRIPT, source, str(nsf), str(log), LOG_TEXT]

    def environment(self) -> Dict[str, str]:
        return dict(os.environ)
