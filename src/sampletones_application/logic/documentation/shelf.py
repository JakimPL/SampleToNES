import os
import shutil
from pathlib import Path
from typing import Final

from sampletones_shared.documentation.site import DocumentationSite
from sampletones_shared.exceptions import DocumentationUnavailableError

HIDDEN_PREFIX: Final[str] = "."
STAGING_SUFFIX: Final[str] = ".staging"
RETIRED_SUFFIX: Final[str] = ".retired"


class DocumentationShelf:
    """Keeps a copy of the shipped documentation in the user's data folder, where the browser reads it.

    The shipped pages may live only as long as a run, since a one-file bundle unpacks itself into
    a temporary folder; the copy outlives the run, so an open page stays readable after the
    application closes. The copy keeps one address across versions, so a page the reader bookmarked
    still opens after an update. It carries the stamp of the pages it was copied from, and a
    different stamp in the installation replaces it whole.
    """

    def __init__(
        self,
        *,
        site: DocumentationSite,
        directory: Path,
    ) -> None:
        self._site = site
        self._copy = DocumentationSite(directory)

    def place(self) -> Path:
        """The index of the copy of the shipped pages, replaced first where it holds other pages.

        The new pages are written beside the copy and swapped in once whole, so the copy is either
        the earlier pages or the new ones.

        Raises:
            DocumentationUnavailableError: If the installation carries no sealed site.
            OSError: If the copy cannot be written.
        """
        stamp = self._site.read_stamp()
        if stamp is None or not self._site.index.is_file():
            raise DocumentationUnavailableError(f"No documentation site lies in {self._site.directory}")

        if self._copy.read_stamp() != stamp:
            self._replace()

        return self._copy.index

    def _replace(self) -> None:
        target = self._copy.directory
        staging = self._beside(STAGING_SUFFIX)
        retired = self._beside(RETIRED_SUFFIX)
        for leftover in (staging, retired):
            if leftover.exists():
                shutil.rmtree(leftover)

        shutil.copytree(self._site.directory, staging)
        if target.exists():
            os.replace(target, retired)

        os.replace(staging, target)
        shutil.rmtree(retired, ignore_errors=True)

    def _beside(self, suffix: str) -> Path:
        target = self._copy.directory
        return target.with_name(f"{HIDDEN_PREFIX}{target.name}{suffix}")
