from dataclasses import dataclass
from typing import Final, List, Tuple

WINDOW_SIZE: Final[int] = 0x100
LONGEST_TOKEN: Final[int] = 0x7F
END_MARK: Final[int] = 0x00
COPY_FLAG: Final[int] = 0x01
LENGTH_SHIFT: Final[int] = 1
LITERAL_HEADER_SIZE: Final[int] = 1
COPY_SIZE: Final[int] = 2
NO_MATCH: Final[int] = 0


@dataclass(frozen=True)
class Stretch:
    """One stretch of packed data: bytes that follow their header, or a copy of bytes written before.

    Attributes:
        copied: Whether the stretch copies from the window rather than carrying its bytes.
        length: How many bytes the stretch unpacks to.
        distance: How far back a copy starts reading, or `NO_MATCH` for literals.
    """

    copied: bool
    length: int
    distance: int


SINGLE_LITERAL: Final[Stretch] = Stretch(copied=False, length=1, distance=NO_MATCH)


def pack(data: bytes) -> bytes:
    """Packs bytes the way the shell unpacks its screen: stretches of literals and copies of what came before.

    A header byte states a length of 1 to 127 above its lowest bit, and that bit says whether the
    bytes follow as literals or are copied from the last 256 bytes written. A copy names the place in
    that window it starts reading at, the window being indexed by the count of bytes written modulo
    256, so a copy from one byte back repeats a byte. A zero header ends the data. The parse is
    optimal: every stretch is cut where the packed data comes out shortest.

    Args:
        data: The bytes to pack.

    Returns:
        bytes: The packed bytes, closed by the end mark.
    """
    packed = bytearray()
    position = 0
    for stretch in _optimal_stretches(data):
        if stretch.copied:
            header = (stretch.length << LENGTH_SHIFT) | COPY_FLAG
            packed += bytes((header, (position - stretch.distance) % WINDOW_SIZE))
        else:
            packed.append(stretch.length << LENGTH_SHIFT)
            packed += data[position : position + stretch.length]
        position += stretch.length

    packed.append(END_MARK)
    return bytes(packed)


def unpack(packed: bytes) -> bytes:
    """Reads packed bytes back, as the shell does.

    Raises:
        ValueError: If the data ends before its end mark.
    """
    window = bytearray(WINDOW_SIZE)
    data = bytearray()
    position = 0
    while position < len(packed):
        header = packed[position]
        if header == END_MARK:
            return bytes(data)

        length = header >> LENGTH_SHIFT
        if header & COPY_FLAG:
            source = packed[position + 1]
            for offset in range(length):
                _write(window, data, window[(source + offset) % WINDOW_SIZE])
            position += COPY_SIZE
        else:
            for value in packed[position + 1 : position + 1 + length]:
                _write(window, data, value)
            position += LITERAL_HEADER_SIZE + length

    raise ValueError("the packed data ends before its end mark")


def _write(window: bytearray, data: bytearray, value: int) -> None:
    """Writes one unpacked byte, which lands in the window at the count of bytes written before it."""
    window[len(data) % WINDOW_SIZE] = value
    data.append(value)


def _optimal_stretches(data: bytes) -> List[Stretch]:
    """The stretches that pack ``data`` shortest, worked out from its end back to its start."""
    size = len(data)
    cost = [0] * (size + 1)
    choice: List[Stretch] = [SINGLE_LITERAL] * size
    for position in range(size - 1, -1, -1):
        best: Tuple[int, Stretch] = (LITERAL_HEADER_SIZE + 1 + cost[position + 1], SINGLE_LITERAL)
        for length in range(2, min(LONGEST_TOKEN, size - position) + 1):
            candidate = LITERAL_HEADER_SIZE + length + cost[position + length]
            if candidate < best[0]:
                best = (candidate, Stretch(copied=False, length=length, distance=NO_MATCH))

        longest, distance = _longest_match(data, position)
        for length in range(1, longest + 1):
            candidate = COPY_SIZE + cost[position + length]
            if candidate < best[0]:
                best = (candidate, Stretch(copied=True, length=length, distance=distance))

        cost[position], choice[position] = best

    stretches: List[Stretch] = []
    position = 0
    while position < size:
        stretches.append(choice[position])
        position += choice[position].length

    return stretches


def _longest_match(data: bytes, position: int) -> Tuple[int, int]:
    """The longest run at ``position`` that repeats bytes within the window, and how far back it reads."""
    longest, nearest = NO_MATCH, NO_MATCH
    reach = min(LONGEST_TOKEN, len(data) - position)
    for distance in range(1, min(WINDOW_SIZE, position) + 1):
        length = 0
        while length < reach and data[position + length] == data[position + length - distance]:
            length += 1

        if length > longest:
            longest, nearest = length, distance

    return longest, nearest
