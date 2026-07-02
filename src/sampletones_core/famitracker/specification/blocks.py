from dataclasses import dataclass
from typing import Final

BLOCK_NAME_LENGTH: Final[int] = 16


@dataclass(frozen=True)
class Block:
    """A FamiTracker module block identity: its name and format version."""

    name: str
    version: int


# Block identities (name, version) — vanilla FamiTracker 0.4.6
BLOCK_PARAMS: Final[Block] = Block("PARAMS", 6)
BLOCK_INFO: Final[Block] = Block("INFO", 1)
BLOCK_HEADER: Final[Block] = Block("HEADER", 3)
BLOCK_INSTRUMENTS: Final[Block] = Block("INSTRUMENTS", 6)
BLOCK_SEQUENCES: Final[Block] = Block("SEQUENCES", 6)
BLOCK_FRAMES: Final[Block] = Block("FRAMES", 3)
BLOCK_PATTERNS: Final[Block] = Block("PATTERNS", 5)
BLOCK_DPCM_SAMPLES: Final[Block] = Block("DPCM SAMPLES", 1)
BLOCK_COMMENTS: Final[Block] = Block("COMMENTS", 1)
