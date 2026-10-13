from dataclasses import dataclass

import pytest

from assets.documentation.markdown.anchors import HeadingAnchors, heading_anchor
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestTheAnchorAHeadingGets(BaseTestSuite):
    """A heading's anchor is the one GitHub gives it: lower case, punctuation and code marks
    dropped, every space a hyphen."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        heading: str
        expected: str

    test_cases = (
        TestCase(label="plain words", heading="Choosing what to convert", expected="choosing-what-to-convert"),
        TestCase(
            label="punctuation", heading="Voices: samples and instruments", expected="voices-samples-and-instruments"
        ),
        TestCase(label="a code span", heading="The `.nsf` file", expected="the-nsf-file"),
        TestCase(label="emphasis", heading="An *important* part", expected="an-important-part"),
        TestCase(label="a lettered heading", heading="A. The file", expected="a-the-file"),
        TestCase(label="hyphens kept", heading="One-shot and loops", expected="one-shot-and-loops"),
        TestCase(label="surrounding spaces", heading="  Padded  ", expected="padded"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_anchor(self, test_case: TestCase) -> None:
        assert heading_anchor(test_case.heading) == test_case.expected


class TestHeadingAnchors:
    def test_a_repeated_heading_is_numbered(self) -> None:
        anchors = HeadingAnchors()

        assert [anchors.claim("Part"), anchors.claim("Part"), anchors.claim("Part")] == ["part", "part-1", "part-2"]

    def test_distinct_headings_keep_their_anchors(self) -> None:
        anchors = HeadingAnchors()

        assert [anchors.claim("First"), anchors.claim("Second")] == ["first", "second"]
