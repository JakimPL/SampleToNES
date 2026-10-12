from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import pytest

from assets.documentation.published import is_published, page_path, published_pages
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestWhichDocumentsArePublished(BaseTestSuite):
    """The site carries the index, the glossary and the user's sections; the rest stays online."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        relative: str
        expected: bool

    test_cases = (
        TestCase(label="the index", relative="index.md", expected=True),
        TestCase(label="the glossary", relative="glossary.md", expected=True),
        TestCase(label="a guide page", relative="guide/converting.md", expected=True),
        TestCase(label="a formats page", relative="formats/nsf.md", expected=True),
        TestCase(label="an api page", relative="api/index.md", expected=True),
        TestCase(label="a development page", relative="development/guidelines.md", expected=False),
        TestCase(label="a test plan", relative="tests/screens.md", expected=False),
        TestCase(label="another root page", relative="CHANGELOG.md", expected=False),
        TestCase(label="a picture in a published folder", relative="guide/picture.webp", expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_answer(self, test_case: TestCase) -> None:
        assert is_published(PurePosixPath(test_case.relative)) is test_case.expected


class TestPublishedPages:
    def test_every_published_document_is_listed_in_order(self, docs: Path) -> None:
        assert published_pages(docs) == [
            PurePosixPath("glossary.md"),
            PurePosixPath("guide/next.md"),
            PurePosixPath("guide/start.md"),
            PurePosixPath("index.md"),
        ]

    def test_a_page_sits_where_its_document_sits(self) -> None:
        assert page_path(PurePosixPath("guide/start.md")) == PurePosixPath("guide/start.html")
