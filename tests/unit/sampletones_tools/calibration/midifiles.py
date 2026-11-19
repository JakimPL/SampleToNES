import io
import tarfile
from pathlib import Path
from typing import Final, List, Sequence, Tuple

TICKS_PER_BEAT: Final[int] = 480
TEMPO: Final[int] = 500_000
SECONDS_PER_TICK: Final[float] = TEMPO / 1e6 / TICKS_PER_BEAT

Message = Tuple[int, bytes]


def _length(value: int) -> bytes:
    groups = [value & 0x7F]
    value >>= 7
    while value:
        groups.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(groups))


def track(name: str, messages: Sequence[Message], *, tempo: bool = False) -> bytes:
    """A track named ``name`` holding ``messages``, each a delta in ticks beside its bytes."""
    body = b"\x00\xff\x03" + _length(len(name)) + name.encode()
    if tempo:
        body += b"\x00\xff\x51\x03" + TEMPO.to_bytes(3, "big")
    for delta, data in messages:
        body += _length(delta) + data
    body += b"\x00\xff\x2f\x00"
    return b"MTrk" + len(body).to_bytes(4, "big") + body


def midi_file(tracks: List[bytes]) -> bytes:
    """A format-1 MIDI file of ``tracks`` at 480 ticks a beat."""
    header = b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big") + len(tracks).to_bytes(2, "big")
    return header + TICKS_PER_BEAT.to_bytes(2, "big") + b"".join(tracks)


def ticks(seconds: float) -> int:
    return round(seconds / SECONDS_PER_TICK)


def nesmdb_piece() -> bytes:
    """A one-second piece in NES-MDB's layout: a pulse note with a volume change, a triangle note, a noise hit."""
    pulse = track(
        "p1",
        [
            (0, bytes([0xB0, 12, 1])),
            (0, bytes([0x90, 69, 12])),
            (ticks(0.5), bytes([0xB0, 11, 6])),
            (ticks(0.5), bytes([0x80, 69, 0])),
        ],
        tempo=True,
    )
    triangle = track("tr", [(0, bytes([0x90, 45, 1])), (ticks(1.0), bytes([0x90, 45, 0]))])
    noise = track("no", [(0, bytes([0xB0, 12, 1])), (0, bytes([0x90, 13, 9])), (ticks(0.25), bytes([0x80, 13, 0]))])
    return midi_file([pulse, triangle, noise])


def nesmdb_archive(directory: Path, member: str) -> Path:
    """A gzipped tar archive holding the piece under ``member``."""
    path = directory / "nesmdb.tar.gz"
    data = nesmdb_piece()
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(member)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return path
