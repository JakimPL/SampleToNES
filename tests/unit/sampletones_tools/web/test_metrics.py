import struct
from pathlib import Path

import pytest

from sampletones_tools.web.paths import FONTS_DIRECTORY
from sampletones_tools.web.typography.metrics import FontMetrics
from sampletones_tools.web.typography.scale import TYPEFACE_FILES


def _font(path: Path, *, units_per_em: int, ascent: int, descent: int) -> Path:
    """A TrueType file holding only the two tables the reader needs."""
    head = bytearray(54)
    struct.pack_into(">H", head, 18, units_per_em)
    hhea = bytearray(36)
    struct.pack_into(">hh", hhea, 4, ascent, descent)
    tables = [(b"head", bytes(head)), (b"hhea", bytes(hhea))]
    offset = 12 + 16 * len(tables)
    directory = struct.pack(">IHHHH", 0x00010000, len(tables), 0, 0, 0)
    body = b""
    for tag, data in tables:
        directory += struct.pack(">4sIII", tag, 0, offset + len(body), len(data))
        body += data
    path.write_bytes(directory + body)
    return path


class TestFontMetrics:
    def test_reads_the_head_and_hhea_tables(self, tmp_path: Path) -> None:
        metrics = FontMetrics.read(_font(tmp_path / "face.ttf", units_per_em=1000, ascent=1100, descent=-300))

        assert (metrics.units_per_em, metrics.ascent, metrics.descent) == (1000, 1100, -300)

    def test_the_pixel_factor_spans_the_ascent_to_the_descent(self) -> None:
        metrics = FontMetrics(units_per_em=1000, ascent=1100, descent=-300)

        assert metrics.em_per_pixel_height == pytest.approx(1000 / 1400)

    @pytest.mark.parametrize("filename", sorted(set(TYPEFACE_FILES.values())))
    def test_every_shipped_regular_face_reads(self, filename: str) -> None:
        metrics = FontMetrics.read(FONTS_DIRECTORY / filename)

        assert 0 < metrics.em_per_pixel_height < 1
