from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
    ScanEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.reconstruction import (
    ReconstructionEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION


def scan_reconstructions(directory: Path) -> ReconstructionScan:
    """Reads a reconstructions directory once, recording its folders and the reconstructions inside.

    Every folder is recorded together with the configuration its name states, and every
    reconstruction file beneath it. This single reading feeds both browser branches, so the two
    views agree on what is on disk.
    """
    return ReconstructionScan(entries=_scan_entries(directory))


def _scan_entries(directory: Path) -> Tuple[ScanEntry, ...]:
    entries: List[ScanEntry] = []
    for path in sorted(directory.iterdir()):
        entry = _scan_path(path)
        if entry is not None:
            entries.append(entry)

    return tuple(entries)


def _scan_path(path: Path) -> Optional[ScanEntry]:
    if path.is_dir():
        return DirectoryEntry(
            path=path,
            config=ConfigDirectoryFields.from_directory_name(path.name),
            entries=_scan_entries(path),
        )

    if path.suffix == EXT_FILE_RECONSTRUCTION:
        return ReconstructionEntry(path=path)

    return None
