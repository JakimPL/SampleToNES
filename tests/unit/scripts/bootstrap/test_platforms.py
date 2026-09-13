from dataclasses import dataclass
from pathlib import Path

import pytest

from bootstrap.platforms import macos
from bootstrap.platforms.factory import platform_named
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import HOMEBREW, HOMEBREW_SITE, MacOS
from bootstrap.platforms.windows import Windows
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestPlatformNamed(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: str
        bundles: bool

    test_cases = (
        TestCase(label="Linux builds a bundle", system="Linux", bundles=True),
        TestCase(label="Windows builds a bundle", system="Windows", bundles=True),
        TestCase(label="macOS runs from source", system="Darwin", bundles=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_system_name_selects_its_platform(self, test_case: TestCase) -> None:
        platform = platform_named(test_case.system)

        assert platform.name == test_case.system
        assert platform.bundles is test_case.bundles

    def test_an_unknown_system_is_refused_by_name(self) -> None:
        with pytest.raises(SystemExit, match="Plan 9"):
            platform_named("Plan 9")


class TestLaunchers(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: str
        release: bool
        expected: str

    test_cases = (
        TestCase(label="a Linux development bundle is one file", system="Linux", release=False, expected="sampletones"),
        TestCase(
            label="a Linux release is a directory beside its launcher",
            system="Linux",
            release=True,
            expected="sampletones/sampletones",
        ),
        TestCase(
            label="a Windows development bundle carries an extension",
            system="Windows",
            release=False,
            expected="sampletones.exe",
        ),
        TestCase(
            label="a Windows release is a directory beside its launcher",
            system="Windows",
            release=True,
            expected="sampletones/sampletones.exe",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_launcher_lies_where_pyinstaller_writes_it(self, test_case: TestCase) -> None:
        launcher = platform_named(test_case.system).launcher(Path("bin"), release=test_case.release)

        assert launcher == Path("bin") / test_case.expected


class TestInterpreters:
    def test_a_posix_environment_runs_bin_python(self) -> None:
        assert Linux().interpreter(Path(".venv-build")) == Path(".venv-build/bin/python")

    def test_a_windows_environment_runs_scripts_python(self) -> None:
        assert Windows().interpreter(Path(".venv-build")) == Path(".venv-build/Scripts/python.exe")


class TestSystemPackages:
    def test_linux_updates_apt_before_installing(self) -> None:
        commands = Linux().system_packages()

        assert [command[:2] for command in commands] == [("sudo", "apt-get"), ("sudo", "apt-get")]
        assert "portaudio19-dev" in commands[1]
        assert "python3-tk" in commands[1]

    def test_macos_installs_portaudio_through_homebrew(self) -> None:
        assert MacOS().system_packages() == ((HOMEBREW, "install", "portaudio"),)

    def test_macos_with_homebrew_has_its_package_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(macos.shutil, "which", lambda name: f"/opt/homebrew/bin/{name}")

        assert MacOS().missing_package_manager() is None

    def test_macos_without_homebrew_names_where_to_get_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(macos.shutil, "which", lambda name: None)

        refusal = MacOS().missing_package_manager()

        assert refusal is not None
        assert HOMEBREW_SITE in refusal

    def test_windows_installs_nothing(self) -> None:
        assert Windows().system_packages() == ()
        assert Windows().missing_package_manager() is None


class TestBuildEnvironment:
    def test_macos_exports_the_portaudio_flags_on_the_native_architecture(self) -> None:
        lines = MacOS().build_environment(machine="arm64", portaudio_prefix="/opt/homebrew/opt/portaudio")

        assert lines == (
            "CFLAGS=-I/opt/homebrew/opt/portaudio/include",
            "LDFLAGS=-L/opt/homebrew/opt/portaudio/lib",
            "ARCHFLAGS=-arch arm64",
        )

    def test_macos_without_homebrew_is_refused(self) -> None:
        with pytest.raises(SystemExit, match="Homebrew"):
            MacOS().build_environment(machine="arm64", portaudio_prefix="")

    def test_other_systems_export_nothing(self) -> None:
        assert Linux().build_environment(machine="x86_64", portaudio_prefix="") == ()
        assert Windows().build_environment(machine="AMD64", portaudio_prefix="") == ()
