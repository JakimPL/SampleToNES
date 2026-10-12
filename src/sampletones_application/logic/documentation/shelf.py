import os
import shutil
from pathlib import Path
from typing import Final

from sampletones_shared.documentation.site import DocumentationSite
from sampletones_shared.exceptions import DocumentationUnavailableError

STAGING_PREFIX: Final[str] = "."
STAGING_SUFFIX: Final[str] = ".staging"


class DocumentationShelf:
    """Keeps a copy of the shipped documentation in the user's data folder, where the browser reads it.

    The shipped pages may live only as long as a run, since a one-file bundle unpacks itself into
    a temporary folder; the copy outlives the run, so an open page stays readable after the
    application closes. A copy is named by the site's stamp, and a site with the same stamp holds
    the same pages, so each version of the documentation is copied once and the copies of other
    versions are let go.
    """

    def __init__(
        self,
        *,
        site: DocumentationSite,
        copies: Path,
    ) -> None:
        self._site = site
        self._copies = copies

    def place(self) -> Path:
        """The index of the copy of the shipped pages, copied first where it is missing.

        A copy is written beside its final place and moved there whole, so a copy under a stamp's
        name holds every page.

        Raises:
            DocumentationUnavailableError: If the installation carries no sealed site.
            OSError: If the copy cannot be written.
        """
        stamp = self._site.read_stamp()
        if stamp is None or not self._site.index.is_file():
            raise DocumentationUnavailableError(f"No documentation site lies in {self._site.directory}")

        copy = DocumentationSite(self._copies / stamp)
        if copy.read_stamp() != stamp:
            self._copy(copy.directory)

        self._let_others_go(stamp)
        return copy.index

    def _copy(self, target: Path) -> None:
        staging = self._copies / f"{STAGING_PREFIX}{target.name}{STAGING_SUFFIX}"
        if staging.exists():
            shutil.rmtree(staging)

        shutil.copytree(self._site.directory, staging)
        if target.exists():
            shutil.rmtree(target)

        os.replace(staging, target)

    def _let_others_go(self, stamp: str) -> None:
        """Removes the copies of other versions, leaving any a running browser still holds open."""
        for entry in self._copies.iterdir():
            if entry.is_dir() and entry.name != stamp and not entry.name.startswith(STAGING_PREFIX):
                shutil.rmtree(entry, ignore_errors=True)
