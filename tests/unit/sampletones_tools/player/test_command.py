from pathlib import Path
from typing import Final, List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.driver import JUMP_ABSOLUTE_OPCODE
from sampletones_shared.exceptions.player import DriverBuildError
from sampletones_tools.player.assembler.layout import BINARY_DIRECTORY

BUILDER: Final[str] = "sampletones_tools.player.assembler.builder.build_driver"
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


def _refuse(command: str) -> None:
    raise AssertionError(f"the checkout guard ran for {command}")


class TestDriver:
    def test_without_a_directory_the_shipped_driver_is_written_from_a_checkout(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        build = RecordedBuild()
        guarded: List[str] = []
        monkeypatch.setattr(BUILDER, build)
        monkeypatch.setattr(GUARD, guarded.append)

        assert dispatch(COMMANDS, ["driver"]) == 0
        assert build.destinations == [BINARY_DIRECTORY]
        assert guarded == ["driver"]
        assert "driver.bin  7 bytes" in capsys.readouterr().out

    def test_a_directory_of_its_own_needs_no_checkout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        build = RecordedBuild()
        monkeypatch.setattr(BUILDER, build)
        monkeypatch.setattr(GUARD, _refuse)

        assert dispatch(COMMANDS, ["driver", "--output", str(tmp_path)]) == 0
        assert build.destinations == [tmp_path]

    def test_a_failing_build_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def fail(destination: Path) -> DriverImage:
            raise DriverBuildError(f"ca65 failed: boom in {destination}")

        monkeypatch.setattr(BUILDER, fail)

        with pytest.raises(SystemExit, match="ca65 failed"):
            dispatch(COMMANDS, ["driver", "--output", str(tmp_path)])
