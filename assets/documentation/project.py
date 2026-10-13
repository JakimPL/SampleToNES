from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DOCUMENTATION_URL_KEY: Final[str] = "Documentation"


@dataclass(frozen=True)
class ProjectFacts:
    """What ``pyproject.toml`` states that the documentation shows: the version, and where the
    documentation lives online."""

    version: str
    documentation_address: str

    @classmethod
    def read(cls, path: Path) -> ProjectFacts:
        """The facts ``path`` states.

        Raises:
            KeyError: If the file names no version or no documentation address.
        """
        with path.open("rb") as stream:
            project = tomllib.load(stream)["project"]

        return cls(
            version=str(project["version"]),
            documentation_address=str(project["urls"][DOCUMENTATION_URL_KEY]),
        )
