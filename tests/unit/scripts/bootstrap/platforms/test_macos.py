from pathlib import Path

import pytest

from bootstrap.platforms import macos
from bootstrap.platforms.macos import ARCHFLAGS, CPU_BACKEND, HOMEBREW, HOMEBREW_SITE, PORTAUDIO, MacOS

PORTAUDIO_PREFIX = "/opt/homebrew/opt/portaudio"


class TestMacOS:
    def test_a_virtual_environment_runs_bin_python(self) -> None:
        assert MacOS().interpreter(Path(".venv-build")) == Path(".venv-build", "bin", "python")

    def test_a_bundle_is_refused_with_the_way_to_run_from_source(self) -> None:
        with pytest.raises(SystemExit, match="make setup"):
            MacOS().bundling()

    def test_portaudio_is_installed_through_homebrew(self) -> None:
        assert MacOS().system_packages() == ((HOMEBREW, "install", PORTAUDIO),)

    def test_with_homebrew_the_package_manager_is_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(macos.shutil, "which", lambda name: f"/opt/homebrew/bin/{name}")

        assert MacOS().missing_package_manager() is None

    def test_without_homebrew_the_refusal_names_where_to_get_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(macos.shutil, "which", lambda name: None)

        refusal = MacOS().missing_package_manager()

        assert refusal is not None
        assert HOMEBREW_SITE in refusal

    def test_the_setup_pins_the_native_architecture(self) -> None:
        variables = MacOS().setup_variables({"PATH": "/usr/bin"}, machine="arm64")

        assert variables == {"PATH": "/usr/bin", ARCHFLAGS: "-arch arm64"}

    def test_a_build_compiles_against_homebrew_s_portaudio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(MacOS, "homebrew_prefix", staticmethod(lambda package: PORTAUDIO_PREFIX))

        assert MacOS().build_flags(machine="arm64") == (
            f"CFLAGS=-I{PORTAUDIO_PREFIX}/include",
            f"LDFLAGS=-L{PORTAUDIO_PREFIX}/lib",
            f"{ARCHFLAGS}=-arch arm64",
        )

    def test_a_build_without_homebrew_s_portaudio_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(MacOS, "homebrew_prefix", staticmethod(lambda package: ""))

        with pytest.raises(SystemExit, match="Homebrew"):
            MacOS().build_flags(machine="arm64")

    def test_the_cpu_backend_is_the_one_it_runs(self) -> None:
        assert MacOS().cpu_backend_reason == CPU_BACKEND
        assert MacOS().nvidia_smi_locations({}) == ()


class TestHomebrewPrefix:
    def test_without_homebrew_the_prefix_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(macos.shutil, "which", lambda name: None)

        assert MacOS.homebrew_prefix(PORTAUDIO) == ""
