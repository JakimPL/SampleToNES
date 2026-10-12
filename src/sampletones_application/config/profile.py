from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sampletones_shared.paths.user import (
    APPLICATION_CONFIG_PATH,
    APPLICATION_STATE_PATH,
    DOCUMENTATION_COPIES_DIRECTORY,
)


@dataclass(frozen=True)
class UserProfile:
    """The places a run keeps its settings, its session and its copy of the documentation in.

    A profile is chosen at startup and travels to the managers that read and write it, which is
    what lets a run be pointed at a location of its own.
    """

    config: Path
    state: Path
    documentation: Path

    @classmethod
    def user(cls) -> UserProfile:
        """The profile in the user's own folders, which is where a normal run reads and writes."""
        return cls(
            config=APPLICATION_CONFIG_PATH,
            state=APPLICATION_STATE_PATH,
            documentation=DOCUMENTATION_COPIES_DIRECTORY,
        )
