from typing import Final

FTM_MAGIC: Final[bytes] = b"FamiTracker Module"
FTM_VERSION: Final[int] = 0x0440
FTM_END_MARKER: Final[bytes] = b"END"

FTI_MAGIC: Final[bytes] = b"FTI"
FTI_VERSION: Final[bytes] = b"2.4"

INFO_STRING_LENGTH: Final[int] = 32
