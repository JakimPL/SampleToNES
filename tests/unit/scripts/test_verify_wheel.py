import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import pytest

from bootstrap.layout import DEPLOYMENT_PACKAGE_PATH, RELEASE_DEPLOYMENT, WHEELS
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

verify_wheel = load_script("verify_wheel.py")

RELEASE_SETTINGS = b"log_level: INFO\nstrict_history: false\n"
DEVELOPMENT_SETTINGS = b"log_level: DEBUG\nstrict_history: true\n"
WHEEL_NAME = "sampletones-0.3.2-py3-none-any.whl"


def _write_wheel(wheel: Path, settings: Sequence[bytes]) -> None:
    """A wheel holding a module and ``settings`` as its deployment file, once per entry."""
    wheel.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("sampletones/__init__.py", "")
            for entry in settings:
                archive.writestr(DEPLOYMENT_PACKAGE_PATH, entry)


@pytest.fixture(name="root")
def root_fixture(tmp_path: Path) -> Path:
    """A repository holding the release settings."""
    release = tmp_path / RELEASE_DEPLOYMENT
    release.parent.mkdir(parents=True)
    release.write_bytes(RELEASE_SETTINGS)
    return tmp_path


class TestWheelFailures(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        settings: Sequence[bytes]
        expected: Optional[str]

    test_cases = (
        TestCase(label="the release settings once", settings=(RELEASE_SETTINGS,), expected=None),
        TestCase(label="the development settings", settings=(DEVELOPMENT_SETTINGS,), expected=RELEASE_DEPLOYMENT),
        TestCase(label="no settings", settings=(), expected="0 copies"),
        TestCase(label="two copies", settings=(RELEASE_SETTINGS, DEVELOPMENT_SETTINGS), expected="2 copies"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_each_wheel_carries_the_release_settings_once(self, root: Path, test_case: TestCase) -> None:
        _write_wheel(root / WHEELS / WHEEL_NAME, test_case.settings)

        failures = verify_wheel.wheel_failures(root)

        if test_case.expected is None:
            assert failures == []
            return

        assert len(failures) == 1
        assert WHEEL_NAME in failures[0]
        assert test_case.expected in failures[0]

    def test_a_build_without_wheels_is_refused(self, root: Path) -> None:
        assert verify_wheel.wheel_failures(root) == [f"No wheel found in {root / WHEELS}"]
