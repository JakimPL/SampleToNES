import struct
import zlib
from typing import Final

import numpy as np
from numpy.typing import NDArray

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import save_binary

SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
HEADER_CHUNK: Final[bytes] = b"IHDR"
DATA_CHUNK: Final[bytes] = b"IDAT"
END_CHUNK: Final[bytes] = b"IEND"
HEADER_FORMAT: Final[str] = ">IIBBBBB"
LENGTH_FORMAT: Final[str] = ">I"
BIT_DEPTH: Final[int] = 8
TRUECOLOR: Final[int] = 2
DEFLATE: Final[int] = 0
ADAPTIVE_FILTERING: Final[int] = 0
NO_INTERLACE: Final[int] = 0
UNFILTERED_ROW: Final[bytes] = b"\x00"
CHANNELS: Final[int] = 3
DIMENSIONS: Final[int] = 3
DEFAULT_COMPRESSION_LEVEL: Final[int] = 6


def chunk(kind: bytes, data: bytes) -> bytes:
    """One chunk of a PNG file: its length, its kind, its data and the checksum over the last two."""
    return struct.pack(LENGTH_FORMAT, len(data)) + kind + data + struct.pack(LENGTH_FORMAT, zlib.crc32(kind + data))


def png_bytes(
    pixels: NDArray[np.uint8],
    *,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> bytes:
    """Encodes a truecolor image as a PNG file, with the standard library alone.

    Every row is stored as it is and the whole image deflated once, which keeps the encoder a few
    lines long and every reader able to open what it writes. A caller writing many large frames
    trades size for speed through ``compression_level``.

    Args:
        pixels: The image as rows of pixels, each pixel its red, green and blue as eight-bit levels.
        compression_level: How hard the image is deflated, from 0 for stored to 9 for smallest.

    Returns:
        bytes: The whole file.

    Raises:
        ValueError: If ``pixels`` is another shape than rows of three-channel pixels, or holds
            anything but eight-bit levels.
    """
    if pixels.ndim != DIMENSIONS or pixels.shape[-1] != CHANNELS:
        raise ValueError(f"a truecolor image is rows of {CHANNELS}-channel pixels, got shape {pixels.shape}")

    if pixels.dtype != np.uint8:
        raise ValueError(f"a truecolor image holds eight-bit levels, got {pixels.dtype}")

    height, width, _ = pixels.shape
    rows = b"".join(UNFILTERED_ROW + pixels[row].tobytes() for row in range(height))
    header = struct.pack(
        HEADER_FORMAT,
        width,
        height,
        BIT_DEPTH,
        TRUECOLOR,
        DEFLATE,
        ADAPTIVE_FILTERING,
        NO_INTERLACE,
    )
    return (
        SIGNATURE
        + chunk(HEADER_CHUNK, header)
        + chunk(DATA_CHUNK, zlib.compress(rows, compression_level))
        + chunk(END_CHUNK, b"")
    )


def write_png(
    filepath: Pathlike,
    pixels: NDArray[np.uint8],
    *,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> None:
    """Writes a truecolor image to a PNG file, the file appearing whole or staying as it was.

    Args:
        filepath: The file to write.
        pixels: The image as rows of pixels, each pixel its red, green and blue as eight-bit levels.
        compression_level: How hard the image is deflated, from 0 for stored to 9 for smallest.

    Raises:
        ValueError: If ``pixels`` is another shape than rows of three-channel pixels, or holds
            anything but eight-bit levels.
        OSError: If the destination cannot be written.
    """
    save_binary(filepath, png_bytes(pixels, compression_level=compression_level))
