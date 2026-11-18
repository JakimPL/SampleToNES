from typing import Final

import pytest

from automation.plugin.hooks import CHILD_TIMEOUT_SECONDS, TIMEOUT_MARKER, TIMEOUT_MARKER_WORDS, child_timeout

pytest_plugins = ["pytester"]

LONG_SECONDS: Final[float] = 1800.0


class TestChildTimeout:
    """The process a scenario runs in lives as long as its marker names, or the tier's own deadline."""

    def test_an_unmarked_item_lives_the_tier_deadline(self, pytester: pytest.Pytester) -> None:
        item = pytester.getitem("def test_func(): pass")

        assert child_timeout(item) == CHILD_TIMEOUT_SECONDS

    def test_a_marked_item_lives_the_seconds_it_names(self, pytester: pytest.Pytester) -> None:
        pytester.makeini(f"[pytest]\nmarkers =\n    {TIMEOUT_MARKER_WORDS}\n")
        item = pytester.getitem(f"import pytest\n@pytest.mark.{TIMEOUT_MARKER}({LONG_SECONDS})\ndef test_func(): pass")

        assert child_timeout(item) == LONG_SECONDS
