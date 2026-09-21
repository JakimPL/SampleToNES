from dataclasses import dataclass

import pytest

from sampletones_shared.deployment.version import compare_versions
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestHowTwoVersionsCompare(BaseTestSuite):
    """Versions compare by their numbers, a shorter one read with its missing parts at zero."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        first: str
        second: str
        expected: int

    test_cases = (
        TestCase(label="the same version", first="2.1", second="2.1", expected=0),
        TestCase(label="a version spelled shorter", first="2.1", second="2.1.0", expected=0),
        TestCase(label="an earlier minor version", first="2.0", second="2.1", expected=-1),
        TestCase(label="a later major version", first="10.0", second="9.9.9", expected=1),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_order_they_stand_in(self, test_case: TestCase) -> None:
        assert compare_versions(test_case.first, test_case.second) == test_case.expected


class TestAMalformedVersion(BaseTestSuite):
    """A version that states no numbers is refused as a malformed value."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        version: str

    test_cases = (
        TestCase(label="words", version="abc"),
        TestCase(label="nothing", version=""),
        TestCase(label="too many parts", version="1.2.3.4"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_it_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValueError):
            compare_versions(test_case.version, "2.1")
