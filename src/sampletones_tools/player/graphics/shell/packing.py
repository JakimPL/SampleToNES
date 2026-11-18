from typing import Final, List

LONGEST_RUN: Final[int] = 128
SHORTEST_REPEAT: Final[int] = 3
REPEAT_HEADER_BASE: Final[int] = 257
END_MARK: Final[int] = 0x80
LITERAL_LIMIT: Final[int] = 0x80


def _repeat_length(data: bytes, start: int) -> int:
    length = 1
    while start + length < len(data) and data[start + length] == data[start] and length < LONGEST_RUN:
        length += 1

    return length


def pack(data: bytes) -> bytes:
    """Packs bytes the way the shell unpacks its screen: runs of one byte and stretches of literals.

    A header below 128 copies that many bytes and one more; a header above 128 repeats the byte
    after it 257 less the header times; 128 ends the data.

    Args:
        data: The bytes to pack.

    Returns:
        bytes: The packed bytes, closed by the end mark.
    """
    packed = bytearray()
    literals: List[int] = []
    position = 0
    while position < len(data):
        length = _repeat_length(data, position)
        if length >= SHORTEST_REPEAT:
            _flush(packed, literals)
            packed += bytes((REPEAT_HEADER_BASE - length, data[position]))
            position += length
            continue

        literals.append(data[position])
        position += 1
        if len(literals) == LONGEST_RUN:
            _flush(packed, literals)

    _flush(packed, literals)
    packed.append(END_MARK)
    return bytes(packed)


def unpack(packed: bytes) -> bytes:
    """Reads packed bytes back, as the shell does.

    Raises:
        ValueError: If the data ends before its end mark.
    """
    data = bytearray()
    position = 0
    while position < len(packed):
        header = packed[position]
        if header == END_MARK:
            return bytes(data)

        if header < LITERAL_LIMIT:
            data += packed[position + 1 : position + header + 2]
            position += header + 2
        else:
            data += bytes([packed[position + 1]]) * (REPEAT_HEADER_BASE - header)
            position += 2

    raise ValueError("the packed data ends before its end mark")


def _flush(packed: bytearray, literals: List[int]) -> None:
    if literals:
        packed.append(len(literals) - 1)
        packed += bytes(literals)
        literals.clear()
