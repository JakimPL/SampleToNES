from typing import Final

PROGRAM_START: Final[int] = 0x8000
PROGRAM_SIZE: Final[int] = 0x8000

RAM_SIZE: Final[int] = 0x0800

NMI_VECTOR: Final[int] = 0xFFFA
RESET_VECTOR: Final[int] = 0xFFFC
IRQ_VECTOR: Final[int] = 0xFFFE
