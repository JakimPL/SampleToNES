from dataclasses import dataclass
from typing import Tuple

import pytest

from sampletones_tools.calibration.board.headings import heading_column, shared_words
from sampletones_tools.calibration.variants import LABEL_SEPARATOR
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


def label(*words: str) -> str:
    return LABEL_SEPARATOR.join(words)


class TestSharedWords(BaseTestSuite):
    """The words every column's name starts with, counted in whole words, once two columns stand side by side."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        names: Tuple[str, ...]
        expected: Tuple[str, ...]

    test_cases: Tuple[TestCase, ...] = (
        TestCase(
            label="leading-words",
            names=(label("cqt", "pe1"), label("cqt", "pe1", "joint"), label("cqt", "pe1", "joint", "fitted")),
            expected=("cqt", "pe1"),
        ),
        TestCase(label="whole-words", names=(label("cqt", "pe1"), label("cqt", "pe10")), expected=("cqt",)),
        TestCase(label="first-word-apart", names=(label("cqt", "pe1"), label("fft", "pe1")), expected=()),
        TestCase(label="lone-column", names=(label("cqt", "pe1", "joint"),), expected=()),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_names_share_their_leading_words(self, test_case: TestCase) -> None:
        assert shared_words(test_case.names) == test_case.expected


class TestHeadingColumn:
    def test_a_heading_holds_the_words_past_the_prefix(self) -> None:
        name = label("cqt", "pe1", "joint", "fitted")

        column = heading_column(name, ("cqt", "pe1"))

        assert (column.name, column.words) == (name, ("joint", "fitted"))

    def test_a_column_named_by_the_prefix_alone_is_the_base(self) -> None:
        assert heading_column(label("cqt", "pe1"), ("cqt", "pe1")).words == ()

    def test_a_column_of_a_group_sharing_nothing_shows_every_word(self) -> None:
        assert heading_column(label("cqt", "pe1"), ()).words == ("cqt", "pe1")
