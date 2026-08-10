import platform
from dataclasses import dataclass

import pytest

from sampletones_application.config.session.application.shortcuts import ShortcutsConfig
from sampletones_application.constants.keybindings import (
    DEFAULT_SCHEME_NAME,
    MACOS_SCHEME_NAME,
    PLATFORM_SCHEME_NAMES,
    platform_scheme_name,
)
from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_shared.utils.system.system import System
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestPlatformScheme(BaseTestSuite):
    """The keyboard a fresh profile opens on, one platform at a time.

    A platform is named as :mod:`platform` reports it, which is what the choice is read from.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: str
        expected: str

    test_cases = (
        TestCase(
            label="linux",
            system="Linux",
            expected=DEFAULT_SCHEME_NAME,
        ),
        TestCase(
            label="windows",
            system="Windows",
            expected=DEFAULT_SCHEME_NAME,
        ),
        TestCase(
            label="macos",
            system="Darwin",
            expected=MACOS_SCHEME_NAME,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_scheme_a_platform_ships(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform, "system", lambda: test_case.system)

        assert platform_scheme_name() == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_fresh_profile_opens_on_it(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A reader who has chosen nothing yet starts on the keys their machine is labelled with."""
        monkeypatch.setattr(platform, "system", lambda: test_case.system)

        assert ShortcutsConfig().scheme == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_build_ships_the_scheme_it_names(
        self,
        test_case: TestCase,
    ) -> None:
        """Every platform's choice reaches a file, so a fresh profile starts on a scheme that loads."""
        assert test_case.expected in ShortcutCatalog.load(KEYBINDINGS_DIRECTORY).names


class TestPlatformCoverage:
    def test_every_supported_platform_names_a_scheme(self) -> None:
        assert set(PLATFORM_SCHEME_NAMES) == set(System)

    def test_a_stored_preference_is_read_ahead_of_the_platform(self) -> None:
        assert ShortcutsConfig(scheme=MACOS_SCHEME_NAME).scheme == MACOS_SCHEME_NAME
