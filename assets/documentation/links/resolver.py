import posixpath
from pathlib import Path, PurePosixPath
from typing import Dict, Final, FrozenSet, Optional, Tuple
from urllib.parse import urljoin

from assets.documentation.published import MARKDOWN_SUFFIX, is_published, page_path

EXTERNAL_PREFIXES: Final[Tuple[str, ...]] = ("http://", "https://", "mailto:")
FRAGMENT_SEPARATOR: Final[str] = "#"
PARENT: Final[str] = ".."
DIRECTORY_INDEX: Final[str] = "index.md"


class BrokenLinkError(ValueError):
    pass


class LinkResolver:
    """Turns a link a document writes into the link its page holds.

    A link to another published document becomes a link to its page, and a link to a folder
    becomes a link to the folder's index or to the first of its pages the navigation lists. A link
    to anything the site leaves out, the development pages among them, becomes a link to the online
    copy, so it still leads somewhere. A link to a missing file or heading fails the build.
    """

    def __init__(
        self,
        docs: Path,
        anchors: Dict[PurePosixPath, FrozenSet[str]],
        folder_pages: Dict[str, PurePosixPath],
        address: str,
    ) -> None:
        self._docs = docs
        self._anchors = anchors
        self._folder_pages = folder_pages
        self._address = address.rstrip("/") + "/"

    def resolve(
        self,
        href: str,
        page: PurePosixPath,
    ) -> str:
        """The link ``href``, written in the document ``page``, as the page's link.

        Raises:
            BrokenLinkError: If the link names a missing file or a missing heading.
        """
        if href.startswith(EXTERNAL_PREFIXES):
            return href

        path, _, fragment = href.partition(FRAGMENT_SEPARATOR)
        if not path:
            self._check_fragment(page, fragment, page, href)
            return href

        target = posixpath.normpath(posixpath.join(page.parent.as_posix(), path))
        if target == PARENT or target.startswith(f"{PARENT}/") or not is_published(PurePosixPath(target)):
            return self._online(target, fragment, page, href)

        relative = PurePosixPath(target)
        if relative not in self._anchors:
            raise BrokenLinkError(f"{page} links to a missing document: {href}")

        self._check_fragment(relative, fragment, page, href)
        return self._page_link(page, relative, fragment)

    def _online(
        self,
        target: str,
        fragment: str,
        page: PurePosixPath,
        href: str,
    ) -> str:
        source = (self._docs / target).resolve()
        if not source.exists():
            raise BrokenLinkError(f"{page} links to a missing file: {href}")

        folder = self._folder_page(target) if source.is_dir() else None
        if folder is not None:
            self._check_fragment(folder, fragment, page, href)
            return self._page_link(page, folder, fragment)

        address = urljoin(self._address, f"{target}/" if source.is_dir() else target)
        return f"{address}{FRAGMENT_SEPARATOR}{fragment}" if fragment else address

    def _folder_page(self, target: str) -> Optional[PurePosixPath]:
        index = PurePosixPath(target) / DIRECTORY_INDEX
        if index in self._anchors:
            return index

        return self._folder_pages.get(target)

    def _check_fragment(
        self,
        target: PurePosixPath,
        fragment: str,
        page: PurePosixPath,
        href: str,
    ) -> None:
        if fragment and target.suffix == MARKDOWN_SUFFIX and fragment not in self._anchors[target]:
            raise BrokenLinkError(f"{page} links to a missing heading: {href}")

    @staticmethod
    def _page_link(
        page: PurePosixPath,
        target: PurePosixPath,
        fragment: str,
    ) -> str:
        link = posixpath.relpath(page_path(target).as_posix(), page.parent.as_posix())
        return f"{link}{FRAGMENT_SEPARATOR}{fragment}" if fragment else link
