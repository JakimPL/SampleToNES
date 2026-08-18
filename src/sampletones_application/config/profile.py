from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_shared.paths.user import APPLICATION_CONFIG_PATH


@dataclass(frozen=True)
class UserProfile:
    """The two files a run keeps its settings and its session in.

    A profile is chosen at startup and travels to the managers that read and write it, which is
    what lets a run be pointed at a location of its own.
    """

    config: Path
    state: Path

    @classmethod
    def user(cls) -> UserProfile:
        """The profile in the user's configuration directory, which is where a normal run reads."""
        return cls(
            config=APPLICATION_CONFIG_PATH,
            state=APPLICATION_STATE_PATH,
        )
