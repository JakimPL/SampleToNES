from typing import Final

# Module file container
FTM_MAGIC: Final[bytes] = b"FamiTracker Module"
FTM_VERSION: Final[int] = 0x0440
FTM_END_MARKER: Final[bytes] = b"END"

# Instrument file container
FTI_MAGIC: Final[bytes] = b"FTI"
FTI_VERSION: Final[bytes] = b"2.4"

# INFO block fixed-width string fields
INFO_STRING_LENGTH: Final[int] = 32
