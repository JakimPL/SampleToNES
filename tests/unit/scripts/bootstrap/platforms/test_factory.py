from dataclasses import dataclass

import pytest

from bootstrap.platforms.factory import platform_named
from bootstrap.platforms.linux import LINUX
from bootstrap.platforms.macos import DARWIN
from bootstrap.platforms.windows import WINDOWS
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestPlatformNamed(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: str

    test_cases = (
        TestCase(label="Linux", system=LINUX),
        TestCase(label="Windows", system=WINDOWS),
        TestCase(label="macOS", system=DARWIN),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_system_name_selects_its_platform(self, test_case: TestCase) -> None:
        assert platform_named(test_case.system).name == test_case.system

    def test_an_unknown_system_is_refused_by_name(self) -> None:
        with pytest.raises(SystemExit, match="Plan 9"):
            platform_named("Plan 9")
