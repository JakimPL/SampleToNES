from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.resources import ASSETS_PACKAGE
from sampletones_shared.utils.hashing import calculate_hash

DOCUMENTATION_DIRECTORY: Final[str] = "documentation"
INDEX_FILE: Final[str] = "index.html"
STAMP_FILE: Final[str] = "stamp"
FULL_DIGEST: Final[int] = 64
ENTRY_SEPARATOR: Final[str] = "\n"


@dataclass(frozen=True)
class DocumentationSite:
    """The HTML documentation as a folder of pages, and the stamp that names its contents.

    The maker writes the stamp last, from the files beside it, so a site whose stamp matches its
    contents was written whole. A copy of the site keyed by its stamp is a copy of these exact pages.
    """

    directory: Path

    @classmethod
    def shipped(cls) -> DocumentationSite:
        """The site that ships with the application, inside its assets package."""
        return cls(package_directory(ASSETS_PACKAGE) / DOCUMENTATION_DIRECTORY)

    @property
    def index(self) -> Path:
        return self.directory / INDEX_FILE

    @property
    def stamp_path(self) -> Path:
        return self.directory / STAMP_FILE

    def read_stamp(self) -> Optional[str]:
        """The stamp the site was written with, or ``None`` where no complete site lies."""
        if not self.stamp_path.is_file():
            return None

        return self.stamp_path.read_text(encoding="utf-8").strip()

    def content_stamp(self) -> str:
        """The stamp the site's files earn now: a hash over every file but the stamp, by path and contents."""
        entries = sorted(
            f"{path.relative_to(self.directory).as_posix()}:{calculate_hash(path.read_bytes(), length=FULL_DIGEST)}"
            for path in self.directory.rglob("*")
            if path.is_file() and path != self.stamp_path
        )
        return calculate_hash(ENTRY_SEPARATOR.join(entries))

    def write_stamp(self) -> str:
        """Seal the site: write the stamp its files earn, and return it."""
        stamp = self.content_stamp()
        self.stamp_path.write_text(stamp + ENTRY_SEPARATOR, encoding="utf-8", newline=ENTRY_SEPARATOR)
        return stamp
