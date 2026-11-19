from typing import Final

from sampletones_player.specification.binary import WORD_SIZE

SHELL_PACKAGE: Final[str] = "sampletones_player.shell"
SHELL_BINARY_DIRECTORY: Final[str] = "binary"
SHELL_CODE_NAME: Final[str] = "shell.bin"
PATTERNS_NAME: Final[str] = "patterns.bin"

ADDRESS_SPACE_END: Final[int] = 0x10000
VECTOR_COUNT: Final[int] = 3
VECTORS_SIZE: Final[int] = VECTOR_COUNT * WORD_SIZE
