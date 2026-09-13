from pathlib import Path

from bootstrap.platforms.linux import Linux


class TestLinux:
    def test_a_virtual_environment_runs_bin_python(self) -> None:
        assert Linux().interpreter(Path(".venv-build")) == Path(".venv-build", "bin", "python")

    def test_a_bundle_launcher_carries_no_extension(self) -> None:
        assert Linux().bundling().launcher(Path("bin"), name="sampletones", release=False) == Path("bin", "sampletones")

    def test_apt_is_updated_before_the_packages_are_installed(self) -> None:
        commands = Linux().system_packages()

        assert [command[:2] for command in commands] == [("sudo", "apt-get"), ("sudo", "apt-get")]
        assert "portaudio19-dev" in commands[1]
        assert "python3-tk" in commands[1]
        assert Linux().missing_package_manager() is None

    def test_the_setup_and_the_build_take_the_variables_as_given(self) -> None:
        assert Linux().setup_variables({"PATH": "/usr/bin"}, machine="x86_64") == {"PATH": "/usr/bin"}
        assert Linux().build_flags(machine="x86_64") == ()

    def test_the_driver_is_looked_up_on_the_path_alone(self) -> None:
        assert Linux().cuda
        assert Linux().nvidia_smi_locations({"SystemRoot": "C:/Windows"}) == ()
