import struct

from sampletones_shared.exceptions import TruncatedDataError


class BinaryWriter:
    """Builds a little-endian byte buffer through named, semantic write methods.

    Binary file writing goes through this class, so raw struct packing stays confined here and
    the writers above it read field by field, the way the format specification states them.
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

    def write_uint16(self, value: int) -> None:
        self._buffer.extend(struct.pack("<H", value))

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


class BinaryReader:
    """Takes a little-endian byte buffer apart through named, semantic read methods.

    Binary file reading goes through this class, so raw struct unpacking stays confined here and
    the readers above it take the fields one by one, the way the format specification states them.
    Every read advances past what it took, so a reader states the layout as a sequence of calls.
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    @property
    def remaining(self) -> int:
        """The bytes left between where the reader stands and the end of the buffer."""
        return len(self._data) - self._offset

    def read_bytes(self, count: int) -> bytes:
        """Takes the next ``count`` bytes.

        Raises:
            TruncatedDataError: If the buffer holds fewer than ``count`` bytes from here.
        """
        self._require(count)
        chunk = self._data[self._offset : self._offset + count]
        self._offset += count
        return chunk

    def read_uint8(self) -> int:
        return self._read("<B")

    def read_int8(self) -> int:
        return self._read("<b")

    def read_uint32(self) -> int:
        return self._read("<I")

    def read_int32(self) -> int:
        return self._read("<i")

    def read_counted_string(self) -> str:
        """Takes a ``uint32`` byte length and the UTF-8 text of that many bytes behind it.

        Raises:
            TruncatedDataError: If the buffer holds fewer bytes than the length states.
            UnicodeDecodeError: If those bytes are not UTF-8 text.
        """
        return self.read_bytes(self.read_uint32()).decode("utf-8")

    def _read(self, fmt: str) -> int:
        size = struct.calcsize(fmt)
        self._require(size)
        (value,) = struct.unpack_from(fmt, self._data, self._offset)
        self._offset += size
        return int(value)

    def _require(self, count: int) -> None:
        if count > self.remaining:
            raise TruncatedDataError(
                f"A read of {count} bytes at offset {self._offset} runs past the {len(self._data)} bytes held"
            )
