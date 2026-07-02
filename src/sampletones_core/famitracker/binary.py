from __future__ import annotations

import struct
from contextlib import contextmanager
from typing import Iterator

from sampletones_core.famitracker.specification.blocks import BLOCK_NAME_LENGTH, Block


class BinaryWriter:
    """Builds a little-endian byte buffer through named, semantic write methods.

    All FamiTracker file writing goes through this class, so raw struct packing
    stays confined here and the higher-level block writers read field-by-field like
    the format specification.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    @property
    def data(self) -> bytes:
        return bytes(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)

    def write_bytes(self, data: bytes) -> None:
        self._buffer.extend(data)

    def write_uint8(self, value: int) -> None:
        self._buffer.extend(struct.pack("<B", value))

    def write_int8(self, value: int) -> None:
        self._buffer.extend(struct.pack("<b", value))

    def write_uint32(self, value: int) -> None:
        self._buffer.extend(struct.pack("<I", value))

    def write_int32(self, value: int) -> None:
        self._buffer.extend(struct.pack("<i", value))

    def write_fixed_string(self, text: str, length: int) -> None:
        """Writes ``text`` as UTF-8 into a fixed ``length``-byte field, NUL-padded.

        Text whose UTF-8 encoding exceeds ``length`` bytes is cut to fit the field.
        """
        encoded = text.encode("utf-8")[:length]
        self._buffer.extend(encoded)
        self._buffer.extend(b"\x00" * (length - len(encoded)))

    def write_counted_string(self, text: str) -> None:
        """Writes a ``uint32`` byte length followed by the UTF-8 bytes of ``text``."""
        encoded = text.encode("utf-8")
        self.write_uint32(len(encoded))
        self._buffer.extend(encoded)

    def write_terminated_string(self, text: str) -> None:
        """Writes the UTF-8 bytes of ``text`` followed by a single NUL terminator."""
        self._buffer.extend(text.encode("utf-8"))
        self._buffer.extend(b"\x00")

    @contextmanager
    def block(self, descriptor: Block) -> Iterator[BinaryWriter]:
        """Frames a named, versioned block around a buffered payload.

        The payload written to the yielded writer is emitted with the block name
        (NUL-padded to :data:`BLOCK_NAME_LENGTH`), the version (``int32``) and the
        payload size (``int32``) in front of it, so the size is known before the
        header is written.
        """
        payload = BinaryWriter()
        yield payload

        body = payload.data
        self._write_block_name(descriptor.name)
        self.write_int32(descriptor.version)
        self.write_int32(len(body))
        self._buffer.extend(body)

    def _write_block_name(self, name: str) -> None:
        encoded = name.encode("ascii")
        if len(encoded) > BLOCK_NAME_LENGTH:
            raise ValueError(f"Block name '{name}' exceeds {BLOCK_NAME_LENGTH} bytes")

        self._buffer.extend(encoded)
        self._buffer.extend(b"\x00" * (BLOCK_NAME_LENGTH - len(encoded)))
