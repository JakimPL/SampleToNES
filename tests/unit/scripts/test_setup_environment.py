from tests.suite.scripts import load_script

setup_environment = load_script("setup_environment.py")


class TestGpuExtra:
    def test_zero_keeps_the_cpu_backend(self) -> None:
        assert setup_environment.gpu_extra("0", system="Linux") is None

    def test_a_named_extra_is_taken_as_given(self) -> None:
        assert setup_environment.gpu_extra("gpu-cuda11", system="Linux") == "gpu-cuda11"

    def test_auto_on_macos_keeps_the_cpu_backend(self) -> None:
        assert setup_environment.gpu_extra("auto", system="Darwin") is None


class TestSetupCommands:
    def test_the_cpu_backend_synchronizes_and_installs_the_bare_package(self) -> None:
        commands = setup_environment.setup_commands(None)

        assert len(commands) == 2
        assert commands[0] == ["uv", "sync", "--group", "dev"]
        assert commands[1] == ["uv", "tool", "install", "--force", "."]

    def test_a_gpu_extra_reaches_both_installs(self) -> None:
        commands = setup_environment.setup_commands("gpu")

        assert commands[0] == ["uv", "sync", "--group", "dev", "--extra", "gpu"]
        assert commands[1] == ["uv", "tool", "install", "--force", ".[gpu]"]


class TestSetupEnvironmentVariables:
    def test_macos_pins_the_native_architecture(self) -> None:
        variables = setup_environment.setup_environment_variables(
            {"PATH": "/usr/bin"}, system="Darwin", machine="arm64"
        )

        assert variables == {"PATH": "/usr/bin", "ARCHFLAGS": "-arch arm64"}

    def test_other_systems_pass_the_variables_through(self) -> None:
        variables = setup_environment.setup_environment_variables(
            {"PATH": "/usr/bin"}, system="Linux", machine="x86_64"
        )

        assert variables == {"PATH": "/usr/bin"}
