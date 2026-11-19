from pathlib import Path
from typing import Final, List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.image import DriverImage
from sampletones_player.shell.image import ShellImage
from sampletones_player.specification.driver import JUMP_ABSOLUTE_OPCODE
from sampletones_shared.exceptions.player import DriverBuildError
from sampletones_tools.player.assembler.layout import BINARY_DIRECTORY, SHELL_DIRECTORY

BUILDER: Final[str] = "sampletones_tools.player.assembler.builder.build_driver"
SHELL_BUILDER: Final[str] = "sampletones_tools.player.assembler.shell.build_shell"
GUARD: Final[str] = "sampletones_tools.checkout.require_checkout"
RETURN_OPCODE: Final[int] = 0x60
CODE: Final[bytes] = bytes((JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, RETURN_OPCODE))
IMAGE: Final[DriverImage] = DriverImage(code=CODE, addresses=DriverAddresses.for_code(len(CODE)))


class RecordedBuild:
    def __init__(self) -> None:
        self.destinations: List[Path] = []

    def __call__(self, destination: Path) -> DriverImage:
        self.destinations.append(destination)
        return IMAGE


class RecordedShellBuild:
    def __init__(self) -> None:
        self.destinations: List[Path] = []
        self.drivers: List[DriverImage] = []

    def __call__(self, destination: Path, driver: DriverImage) -> ShellImage:
        self.destinations.append(destination)
        self.drivers.append(driver)
        return ShellImage.load()


def _refuse(command: str) -> None:
    raise AssertionError(f"the checkout guard ran for {command}")


class TestDriver:
    def test_without_a_directory_the_shipped_driver_is_written_from_a_checkout(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        build = RecordedBuild()
        shell_build = RecordedShellBuild()
        guarded: List[str] = []
        monkeypatch.setattr(BUILDER, build)
        monkeypatch.setattr(SHELL_BUILDER, shell_build)
        monkeypatch.setattr(GUARD, guarded.append)

        assert dispatch(COMMANDS, ["driver"]) == 0
        assert build.destinations == [BINARY_DIRECTORY]
        assert shell_build.destinations == [SHELL_DIRECTORY]
        assert guarded == ["driver"]
        printed = capsys.readouterr().out
        assert "driver.bin  7 bytes" in printed
        assert "shell.bin" in printed

    def test_the_shell_is_built_around_the_driver_just_built(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        shell_build = RecordedShellBuild()
        monkeypatch.setattr(BUILDER, RecordedBuild())
        monkeypatch.setattr(SHELL_BUILDER, shell_build)

        assert dispatch(COMMANDS, ["driver", "--output", str(tmp_path)]) == 0
        assert shell_build.drivers == [IMAGE]
        assert shell_build.destinations == [tmp_path]

    def test_a_directory_of_its_own_needs_no_checkout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        build = RecordedBuild()
        monkeypatch.setattr(BUILDER, build)
        monkeypatch.setattr(SHELL_BUILDER, RecordedShellBuild())
        monkeypatch.setattr(GUARD, _refuse)

        assert dispatch(COMMANDS, ["driver", "--output", str(tmp_path)]) == 0
        assert build.destinations == [tmp_path]

    def test_a_failing_build_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def fail(destination: Path) -> DriverImage:
            raise DriverBuildError(f"ca65 failed: boom in {destination}")

        monkeypatch.setattr(BUILDER, fail)

        with pytest.raises(SystemExit, match="ca65 failed"):
            dispatch(COMMANDS, ["driver", "--output", str(tmp_path)])
