from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Startup:
    """The documents a scenario's application opens as it starts, as ``sampletones open`` hands them over.

    Attributes:
        reconstruction: The reconstruction open on the Reconstructions tab, if any.
        project: The project open in the Sequencer, if any.
    """

    reconstruction: Optional[Path]
    project: Optional[Path]
