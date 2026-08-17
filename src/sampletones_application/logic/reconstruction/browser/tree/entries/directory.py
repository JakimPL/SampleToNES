from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from sampletones_core.reconstructions.converter.paths.fields import (
    ConfigDirectoryFields,
)

if TYPE_CHECKING:
    from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
        ScanEntry,
    )


@dataclass(frozen=True)
class DirectoryEntry:
    """A folder a scan met, holding the configuration its name states and the entries inside it.

    A folder whose name encodes a reconstruction configuration carries those fields, read once here,
    so every branch builder states the configuration from the record it already has.
    """

    path: Path
    config: Optional[ConfigDirectoryFields]
    entries: Tuple["ScanEntry", ...]

    @property
    def name(self) -> str:
        return self.path.name
