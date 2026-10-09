from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final, Tuple


class ReconstructionPathState(StrEnum):
    """Whether a path can be shown for a reconstruction location.

    ``AVAILABLE`` carries one resolvable path. ``MULTIPLE`` carries several paths recorded
    for one location (a stems reconstruction's source files). ``NOT_FOUND`` marks a
    recorded path whose file is absent on this machine. ``NOT_APPLICABLE`` marks a
    location that a reconstruction does not have (a sequencer sample keeps no file
    locations). ``EMPTY`` is the resting state when no reconstruction is loaded.
    """

    AVAILABLE = "available"
    MULTIPLE = "multiple"
    NOT_FOUND = "not_found"
    NOT_APPLICABLE = "not_applicable"
    EMPTY = "empty"

    @classmethod
    def from_source_paths(
        cls,
        source_paths: Tuple[Path, ...],
    ) -> ReconstructionPathState:
        """Returns the state a recorded location takes: not-applicable with no path,
        available with one, multiple with several."""
        if not source_paths:
            return cls.NOT_APPLICABLE

        if len(source_paths) == 1:
            return cls.AVAILABLE

        return cls.MULTIPLE


RECORDED_PATH_STATES: Final[Tuple[ReconstructionPathState, ...]] = (
    ReconstructionPathState.AVAILABLE,
    ReconstructionPathState.MULTIPLE,
    ReconstructionPathState.NOT_FOUND,
)

PLAYABLE_PATH_STATES: Final[Tuple[ReconstructionPathState, ...]] = (
    ReconstructionPathState.AVAILABLE,
    ReconstructionPathState.MULTIPLE,
)
