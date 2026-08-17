from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReconstructionEntry:
    """A reconstruction file a scan met, named by the audio it reconstructs."""

    path: Path

    @property
    def name(self) -> str:
        return self.path.stem
