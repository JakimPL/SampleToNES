from dataclasses import dataclass
from pathlib import Path

import pytest

from bootstrap.platforms.bundling import Bundling
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

NAME = "sampletones"


def _bundling(executable_suffix: str) -> Bundling:
    return Bundling(
        icon="icon.png",
        executable_suffix=executable_suffix,
        pyaudio_advice="",
        tkinter_advice="",
        tkinter_warning="",
    )


class TestLauncher(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        suffix: str
        release: bool
        expected: Path

    test_cases = (
        TestCase(label="a development bundle is one file", suffix="", release=False, expected=Path("bin", NAME)),
        TestCase(
            label="a release is a directory beside its launcher",
            suffix="",
            release=True,
            expected=Path("bin", NAME, NAME),
        ),
        TestCase(
            label="the suffix ends the launcher's name",
            suffix=".exe",
            release=True,
            expected=Path("bin", NAME, f"{NAME}.exe"),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_launcher_lies_where_pyinstaller_writes_it(self, test_case: TestCase) -> None:
        launcher = _bundling(test_case.suffix).launcher(Path("bin"), name=NAME, release=test_case.release)

        assert launcher == test_case.expected
