import posixpath
import re
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Dict, Final, List, Optional, Set, Tuple

import pytest

from assets.documentation.build import SiteRequest, build_site
from assets.documentation.paths import DOCS_DIRECTORY, PROJECT_FILE
from assets.documentation.published import INDEX_PAGE, page_path, published_pages
from sampletones_shared.documentation.site import DocumentationSite

EXTERNAL: Final[Tuple[str, ...]] = ("http://", "https://", "mailto:")
NETWORK_URL: Final[re.Pattern[str]] = re.compile(r"url\(\s*[\"']?(?:https?:)?//")
FRAGMENT_SEPARATOR: Final[str] = "#"
CURRENT_PAGE: Final[str] = "page"


class PageReader(HTMLParser):
    """The ids a page holds, the links it follows, the files it loads and its marked navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: List[str] = []
        self.links: List[str] = []
        self.loads: List[str] = []
        self.navigation: List[str] = []
        self.current: List[str] = []
        self._in_navigation = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "nav":
            self._in_navigation = True
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
            if self._in_navigation:
                self.navigation.append(attributes["href"])
                if attributes.get("aria-current") == CURRENT_PAGE:
                    self.current.append(attributes["href"])
        if tag == "link":
            self.loads.append(attributes["href"])
        if tag in ("img", "script") and "src" in attributes:
            self.loads.append(attributes["src"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav":
            self._in_navigation = False


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> DocumentationSite:
    output = tmp_path_factory.mktemp("documentation") / "site"
    return build_site(SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=output))


@pytest.fixture(scope="module")
def readers(site: DocumentationSite) -> Dict[PurePosixPath, PageReader]:
    readers: Dict[PurePosixPath, PageReader] = {}
    for path in sorted(site.directory.rglob("*.html")):
        reader = PageReader()
        reader.feed(path.read_text(encoding="utf-8"))
        readers[PurePosixPath(path.relative_to(site.directory).as_posix())] = reader

    return readers


def target(page: PurePosixPath, href: str) -> Tuple[PurePosixPath, str]:
    path, _, fragment = href.partition(FRAGMENT_SEPARATOR)
    if not path:
        return page, fragment

    return PurePosixPath(posixpath.normpath(posixpath.join(page.parent.as_posix(), path))), fragment


class TestTheShippedDocumentation:
    def test_every_published_document_is_a_page(self, readers: Dict[PurePosixPath, PageReader]) -> None:
        assert sorted(readers) == sorted(page_path(relative) for relative in published_pages(DOCS_DIRECTORY))

    def test_the_site_is_sealed(self, site: DocumentationSite) -> None:
        assert site.read_stamp() == site.content_stamp()

    def test_every_page_link_reaches_a_file_and_its_heading(
        self,
        site: DocumentationSite,
        readers: Dict[PurePosixPath, PageReader],
    ) -> None:
        broken: List[str] = []
        for page, reader in readers.items():
            for href in reader.links:
                if href.startswith(EXTERNAL):
                    continue

                destination, fragment = target(page, href)
                if not (site.directory / destination).is_file():
                    broken.append(f"{page}: {href}")
                elif fragment and fragment not in readers[destination].ids:
                    broken.append(f"{page}: {href}")

        assert broken == []

    def test_every_file_a_page_loads_lies_in_the_site(
        self,
        site: DocumentationSite,
        readers: Dict[PurePosixPath, PageReader],
    ) -> None:
        missing = [
            f"{page}: {source}"
            for page, reader in readers.items()
            for source in reader.loads
            if source.startswith(EXTERNAL) or not (site.directory / target(page, source)[0]).is_file()
        ]

        assert missing == []

    def test_no_stylesheet_reaches_the_network(self, site: DocumentationSite) -> None:
        reaching = [
            path.name for path in site.directory.rglob("*.css") if NETWORK_URL.search(path.read_text(encoding="utf-8"))
        ]

        assert reaching == []

    def test_no_page_links_a_document_source(self, readers: Dict[PurePosixPath, PageReader]) -> None:
        sources = [
            f"{page}: {href}"
            for page, reader in readers.items()
            for href in reader.links
            if not href.startswith(EXTERNAL) and href.partition(FRAGMENT_SEPARATOR)[0].endswith(".md")
        ]

        assert sources == []

    def test_every_id_on_a_page_is_its_own(self, readers: Dict[PurePosixPath, PageReader]) -> None:
        repeated: Dict[str, Set[str]] = {}
        for page, reader in readers.items():
            seen: Set[str] = set()
            for identifier in reader.ids:
                if identifier in seen:
                    repeated.setdefault(str(page), set()).add(identifier)
                seen.add(identifier)

        assert repeated == {}

    def test_the_navigation_reaches_every_page(self, readers: Dict[PurePosixPath, PageReader]) -> None:
        index = readers[page_path(INDEX_PAGE)]
        reached = {target(page_path(INDEX_PAGE), href)[0] for href in index.navigation}

        assert set(readers) <= reached

    def test_each_page_marks_itself_once(self, readers: Dict[PurePosixPath, PageReader]) -> None:
        for page, reader in readers.items():
            assert [target(page, href)[0] for href in reader.current] == [page], page
