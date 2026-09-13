from pathlib import Path

from bootstrap.platforms.windows import Windows


class TestWindows:
    def test_a_virtual_environment_runs_scripts_python(self) -> None:
        assert Windows().interpreter(Path(".venv-build")) == Path(".venv-build", "Scripts", "python.exe")

    def test_a_bundle_launcher_carries_the_executable_extension(self) -> None:
        launcher = Windows().bundling().launcher(Path("bin"), name="sampletones", release=True)

        assert launcher == Path("bin", "sampletones", "sampletones.exe")

    def test_the_installer_carries_every_system_package(self) -> None:
        assert Windows().system_packages() == ()
        assert Windows().missing_package_manager() is None

    def test_the_setup_and_the_build_take_the_variables_as_given(self) -> None:
        assert Windows().setup_variables({"PATH": "C:/Python"}, machine="AMD64") == {"PATH": "C:/Python"}
        assert Windows().build_flags(machine="AMD64") == ()

    def test_the_driver_s_fixed_locations_are_read_from_the_variables_that_are_set(self) -> None:
        locations = Windows().nvidia_smi_locations({"SystemRoot": "C:/Windows"})

        assert Windows().cuda
        assert locations == (Path("C:/Windows", "System32", "nvidia-smi.exe"),)
