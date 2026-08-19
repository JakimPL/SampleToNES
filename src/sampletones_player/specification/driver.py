from typing import Final

from sampletones_player.specification.nsf import PROGRAM_START

DRIVER_PACKAGE: Final[str] = "sampletones_player.driver"
DRIVER_CODE_NAME: Final[str] = "driver.bin"

MAX_ADDRESS: Final[int] = 0xFFFF

JUMP_ABSOLUTE_OPCODE: Final[int] = 0x4C
JUMP_INSTRUCTION_SIZE: Final[int] = 3
LOAD_ADDRESS: Final[int] = PROGRAM_START
INIT_ADDRESS: Final[int] = LOAD_ADDRESS
PLAY_ADDRESS: Final[int] = LOAD_ADDRESS + JUMP_INSTRUCTION_SIZE
