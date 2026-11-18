import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Tuple

import numpy as np
import pytest
from numpy.typing import NDArray

from sampletones_shared.utils.png import (
    BIT_DEPTH,
    CHANNELS,
    DATA_CHUNK,
    END_CHUNK,
    HEADER_CHUNK,
    HEADER_FORMAT,
    LENGTH_FORMAT,
    SIGNATURE,
    TRUECOLOR,
    png_bytes,
    write_png,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

LENGTH_SIZE: Final[int] = struct.calcsize(LENGTH_FORMAT)
KIND_SIZE: Final[int] = 4
FILTER_SIZE: Final[int] = 1
STORED: Final[int] = 0
SMALLEST: Final[int] = 9
SEED: Final[int] = 7


def chunks_of(data: bytes) -> List[Tuple[bytes, bytes]]:
    """Reads a PNG file back into its chunks, holding each to the checksum it carries."""
    assert data.startswith(SIGNATURE)
    position = len(SIGNATURE)
    chunks: List[Tuple[bytes, bytes]] = []
    while position < len(data):
        (length,) = struct.unpack_from(LENGTH_FORMAT, data, position)
        kind = data[position + LENGTH_SIZE : position + LENGTH_SIZE + KIND_SIZE]
        body = data[position + LENGTH_SIZE + KIND_SIZE : position + LENGTH_SIZE + KIND_SIZE + length]
        (checksum,) = struct.unpack_from(LENGTH_FORMAT, data, position + LENGTH_SIZE + KIND_SIZE + length)
        assert checksum == zlib.crc32(kind + body)
        chunks.append((kind, body))
        position += LENGTH_SIZE + KIND_SIZE + length + LENGTH_SIZE

    return chunks


def pixels_of(data: bytes) -> NDArray[np.uint8]:
    """Reads the pixels a PNG file of unfiltered truecolor rows holds."""
    chunks: Dict[bytes, bytes] = dict(chunks_of(data))
    width, height, *_ = struct.unpack(HEADER_FORMAT, chunks[HEADER_CHUNK])
    rows = np.frombuffer(zlib.decompress(chunks[DATA_CHUNK]), dtype=np.uint8).reshape(
        height, FILTER_SIZE + width * CHANNELS
    )
    assert not rows[:, :FILTER_SIZE].any()
    return rows[:, FILTER_SIZE:].reshape(height, width, CHANNELS)


def image(height: int, width: int) -> NDArray[np.uint8]:
    generator = np.random.default_rng(SEED)
    return generator.integers(0, 256, size=(height, width, CHANNELS), dtype=np.uint8)


class TestTheFileAnImageBecomes(BaseTestSuite):
    """The PNG format's own constants are the contract, so the cases spell them out."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        height: int
        width: int
        compression_level: int

    test_cases = (
        TestCase(height=1, width=1, compression_level=SMALLEST, label="a single pixel"),
        TestCase(height=3, width=5, compression_level=SMALLEST, label="wider than tall"),
        TestCase(height=7, width=2, compression_level=SMALLEST, label="taller than wide"),
        TestCase(height=4, width=4, compression_level=STORED, label="stored without deflating"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pixels_read_back_as_written(self, test_case: TestCase) -> None:
        pixels = image(test_case.height, test_case.width)

        encoded = png_bytes(pixels, compression_level=test_case.compression_level)

        assert np.array_equal(pixels_of(encoded), pixels)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_header_states_the_size_and_the_truecolor_form(self, test_case: TestCase) -> None:
        encoded = png_bytes(image(test_case.height, test_case.width), compression_level=test_case.compression_level)

        width, height, depth, color_type, *_ = struct.unpack(HEADER_FORMAT, dict(chunks_of(encoded))[HEADER_CHUNK])

        assert (width, height, depth, color_type) == (test_case.width, test_case.height, BIT_DEPTH, TRUECOLOR)

    def test_the_chunks_stand_in_the_order_a_reader_expects(self) -> None:
        kinds = [kind for kind, _ in chunks_of(png_bytes(image(2, 2)))]

        assert kinds == [HEADER_CHUNK, DATA_CHUNK, END_CHUNK]

    def test_a_harder_compression_writes_a_file_no_larger(self) -> None:
        pixels = np.zeros((16, 16, CHANNELS), dtype=np.uint8)

        assert len(png_bytes(pixels, compression_level=SMALLEST)) <= len(png_bytes(pixels, compression_level=STORED))


class TestAnImageTheEncoderRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        pixels: NDArray[np.generic]
        expected: str

    test_cases = (
        TestCase(pixels=np.zeros((2, 2), dtype=np.uint8), expected="rows of", label="a single channel"),
        TestCase(pixels=np.zeros((2, 2, 4), dtype=np.uint8), expected="rows of", label="four channels"),
        TestCase(pixels=np.zeros((2, 2, 3), dtype=np.float32), expected="eight-bit", label="fractions"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_what_an_image_is(self, test_case: TestCase) -> None:
        with pytest.raises(ValueError, match=test_case.expected):
            png_bytes(test_case.pixels)  # type: ignore[arg-type]


class TestWritingAnImage(BaseTestSuite):
    def test_the_file_holds_the_encoded_image(self, tmp_path: Path) -> None:
        pixels = image(3, 3)
        filepath = tmp_path / "image.png"

        write_png(filepath, pixels)

        assert filepath.read_bytes() == png_bytes(pixels)
