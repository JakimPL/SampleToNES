from typing import Final

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.image import DriverImage
from sampletones_player.shell.image import ShellImage
from sampletones_player.specification.driver import JUMP_ABSOLUTE_OPCODE
from sampletones_tools.player.assembler.report import layout_lines, shell_lines

RETURN_OPCODE: Final[int] = 0x60
CODE: Final[bytes] = bytes((JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, RETURN_OPCODE))


class TestLayoutLines:
    def test_the_figures_a_reader_checks_against_the_header(self) -> None:
        image = DriverImage(code=CODE, addresses=DriverAddresses.for_code(len(CODE)))

        lines = layout_lines(image)

        assert lines[0] == "driver.bin  7 bytes, $8000-$8006"
        assert lines[1:] == ["init        $8000", "play        $8003", "song        $8007"]


class TestShellLines:
    def test_the_length_the_start_and_the_routines_the_console_enters(self) -> None:
        shell = ShellImage.load()
        frame, power_on, interrupt = shell.vectors

        lines = shell_lines(shell)

        assert lines[0] == f"shell.bin   {len(shell.code)} bytes, ${shell.start:04X}-$FFFF"
        assert lines[1:] == [
            f"reset       ${power_on:04X}",
            f"frame       ${frame:04X}",
            f"interrupt   ${interrupt:04X}",
        ]
