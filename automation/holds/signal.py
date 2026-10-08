from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReleaseSignal:
    """A file whose appearance lets held work carry on, which a worker process sees as well as the scenario."""

    path: Path

    def release(self) -> None:
        """Creates the file, which lets the held work carry on."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def is_released(self) -> bool:
        """Whether the file exists, which is whether the work was let go."""
        return self.path.exists()
