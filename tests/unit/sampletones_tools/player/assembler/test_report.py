from typing import Final

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.driver.image import DriverImage
from sampletones_player.specification.driver import JUMP_ABSOLUTE_OPCODE
from sampletones_tools.player.assembler.report import layout_lines

RETURN_OPCODE: Final[int] = 0x60
CODE: Final[bytes] = bytes((JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, JUMP_ABSOLUTE_OPCODE, 0x00, 0x80, RETURN_OPCODE))


class TestLayoutLines:
    def test_the_figures_a_reader_checks_against_the_header(self) -> None:
        image = DriverImage(code=CODE, addresses=DriverAddresses.for_code(len(CODE)))

        lines = layout_lines(image)

        assert lines[0] == "driver.bin  7 bytes, $8000-$8006"
        assert lines[1:] == ["init        $8000", "play        $8003", "song        $8007"]
