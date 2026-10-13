from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict

import pytest

from assets.documentation.links.resolver import BrokenLinkError, LinkResolver
from assets.documentation.navigation import Navigation
from assets.documentation.pages.model import ParsedPage
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.assets.documentation.conftest import ADDRESS

START = PurePosixPath("guide/start.md")


@pytest.fixture
def resolver(
    docs: Path,
    pages: Dict[PurePosixPath, ParsedPage],
    navigation: Navigation,
) -> LinkResolver:
    return LinkResolver(
        docs,
        {relative: page.anchors for relative, page in pages.items()},
        navigation.folder_pages,
        ADDRESS,
    )


class TestWhereALinkLeads(BaseTestSuite):
    """A link written in a document leads to the page, the heading or the online copy it means."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        href: str
        page: str
        expected: str

    test_cases = (
        TestCase(
            label="an external address",
            href="https://example.com/a",
            page="guide/start.md",
            expected="https://example.com/a",
        ),
        TestCase(
            label="a mail address",
            href="mailto:someone@example.com",
            page="index.md",
            expected="mailto:someone@example.com",
        ),
        TestCase(label="a heading on the same page", href="#first-part", page="guide/start.md", expected="#first-part"),
        TestCase(label="a page beside it", href="next.md", page="guide/start.md", expected="next.html"),
        TestCase(
            label="a heading on a page beside it",
            href="next.md#second-part",
            page="guide/start.md",
            expected="next.html#second-part",
        ),
        TestCase(label="a page in a folder", href="guide/start.md", page="index.md", expected="guide/start.html"),
        TestCase(
            label="a page up a folder",
            href="../glossary.md#term",
            page="guide/start.md",
            expected="../glossary.html#term",
        ),
        TestCase(label="a folder without an index", href="./", page="guide/start.md", expected="start.html"),
        TestCase(label="a folder named from above", href="guide/", page="index.md", expected="guide/start.html"),
        TestCase(
            label="a development page",
            href="../development/notes.md",
            page="guide/start.md",
            expected=f"{ADDRESS}/development/notes.md",
        ),
        TestCase(
            label="a development folder", href="development/", page="index.md", expected=f"{ADDRESS}/development/"
        ),
        TestCase(
            label="a picture",
            href="../images/picture.webp",
            page="guide/start.md",
            expected=f"{ADDRESS}/images/picture.webp",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_link(self, test_case: TestCase, resolver: LinkResolver) -> None:
        assert resolver.resolve(test_case.href, PurePosixPath(test_case.page)) == test_case.expected


class TestABrokenLink(BaseTestSuite):
    """A link to a missing file or a missing heading fails the build, wherever it points."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        href: str

    test_cases = (
        TestCase(label="a missing heading here", href="#nowhere"),
        TestCase(label="a missing page", href="missing.md"),
        TestCase(label="a missing heading on a page", href="next.md#nowhere"),
        TestCase(label="a missing development page", href="../development/missing.md"),
        TestCase(label="a file above the docs", href="../../outside.md"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_it_is_refused(self, test_case: TestCase, resolver: LinkResolver) -> None:
        with pytest.raises(BrokenLinkError):
            resolver.resolve(test_case.href, START)


class TestAFolderWithAnIndex:
    def test_a_folder_leads_to_its_index(
        self,
        docs: Path,
        pages: Dict[PurePosixPath, ParsedPage],
        navigation: Navigation,
    ) -> None:
        anchors = {relative: page.anchors for relative, page in pages.items()}
        anchors[PurePosixPath("guide/index.md")] = frozenset()
        resolver = LinkResolver(docs, anchors, navigation.folder_pages, ADDRESS)

        assert resolver.resolve("guide/", PurePosixPath("index.md")) == "guide/index.html"
