from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final

TABLE_COUNT_OFFSET: Final[int] = 4
TABLE_RECORDS_OFFSET: Final[int] = 12
TABLE_RECORD_SIZE: Final[int] = 16
TABLE_RECORD_FORMAT: Final[str] = ">4sIII"
HEAD_TAG: Final[bytes] = b"head"
HHEA_TAG: Final[bytes] = b"hhea"
UNITS_PER_EM_OFFSET: Final[int] = 18
ASCENT_OFFSET: Final[int] = 4


@dataclass(frozen=True)
class FontMetrics:
    """A TrueType face's vertical metrics, as its ``head`` and ``hhea`` tables state them."""

    units_per_em: int
    ascent: int
    descent: int

    @classmethod
    def read(cls, path: Path) -> FontMetrics:
        """The metrics of the TrueType file at ``path``.

        Raises:
            KeyError: If the file lacks a ``head`` or an ``hhea`` table.
        """
        data = path.read_bytes()
        tables = cls._table_offsets(data)
        (units_per_em,) = struct.unpack_from(">H", data, tables[HEAD_TAG] + UNITS_PER_EM_OFFSET)
        ascent, descent = struct.unpack_from(">hh", data, tables[HHEA_TAG] + ASCENT_OFFSET)
        return cls(units_per_em=units_per_em, ascent=ascent, descent=descent)

    @property
    def em_per_pixel_height(self) -> float:
        """Ems in one unit of the height the application sizes a font by.

        DearPyGui sizes a font by the span from its ascent to its descent, and CSS by its em, so a
        CSS size equals the application's size times this factor.
        """
        return self.units_per_em / (self.ascent - self.descent)

    @staticmethod
    def _table_offsets(data: bytes) -> Dict[bytes, int]:
        (count,) = struct.unpack_from(">H", data, TABLE_COUNT_OFFSET)
        offsets: Dict[bytes, int] = {}
        for index in range(count):
            tag, _, offset, _ = struct.unpack_from(
                TABLE_RECORD_FORMAT, data, TABLE_RECORDS_OFFSET + index * TABLE_RECORD_SIZE
            )
            offsets[tag] = offset

        return offsets
