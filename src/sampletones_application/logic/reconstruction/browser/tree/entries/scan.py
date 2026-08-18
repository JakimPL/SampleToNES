from dataclasses import dataclass
from typing import List, Sequence, Tuple

from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
    ScanEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.reconstruction import (
    ReconstructionEntry,
)


@dataclass(frozen=True)
class ReconstructionScan:
    """One reading of a reconstructions directory, shared by every browser branch.

    Both branches describe the same disk because both describe this record: the configuration view
    follows the entries as they sit, and the sample view regroups them by the audio they came from.
    """

    entries: Tuple[ScanEntry, ...]

    @property
    def reconstructions(self) -> Tuple[ReconstructionEntry, ...]:
        return self.collect_reconstructions(self.entries)

    @staticmethod
    def collect_reconstructions(
        entries: Sequence[ScanEntry],
    ) -> Tuple[ReconstructionEntry, ...]:
        """Flattens scanned entries into the reconstructions they hold, in the order the scan met them."""
        collected: List[ReconstructionEntry] = []
        for entry in entries:
            match entry:
                case ReconstructionEntry():
                    collected.append(entry)
                case DirectoryEntry():
                    collected.extend(ReconstructionScan.collect_reconstructions(entry.entries))

        return tuple(collected)
