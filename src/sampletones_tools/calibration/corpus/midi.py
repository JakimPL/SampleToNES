from dataclasses import dataclass, field
from typing import Dict, Final, List, Tuple

HEADER_CHUNK: Final[bytes] = b"MThd"
TRACK_CHUNK: Final[bytes] = b"MTrk"
META_EVENT: Final[int] = 0xFF
SYSEX_EVENTS: Final[Tuple[int, int]] = (0xF0, 0xF7)
TRACK_NAME: Final[int] = 0x03
SET_TEMPO: Final[int] = 0x51
NOTE_OFF: Final[int] = 0x80
NOTE_ON: Final[int] = 0x90
CONTROL_CHANGE: Final[int] = 0xB0
ONE_BYTE_MESSAGES: Final[Tuple[int, int]] = (0xC0, 0xD0)
STATUS_BIT: Final[int] = 0x80
SMPTE_BIT: Final[int] = 0x8000
DEFAULT_TEMPO: Final[int] = 500_000
MICROSECONDS: Final[float] = 1e6


class MidiFormatError(ValueError):
    """Raised when bytes hold no standard MIDI file this reader takes."""


@dataclass(frozen=True)
class Note:
    """A note a track plays, in seconds.

    Attributes:
        start: When it starts.
        end: When it ends.
        pitch: The note number.
        velocity: How hard it is struck.
    """

    start: float
    end: float
    pitch: int
    velocity: int


@dataclass
class Track:
    """What one named track plays: its notes, and each controller's values over time, in seconds."""

    notes: List[Note] = field(default_factory=list)
    controllers: Dict[int, List[Tuple[float, int]]] = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    """A channel message at the tick it falls on: its kind, without the channel, and its two data bytes."""

    tick: int
    status: int
    first: int
    second: int


def read_midi(data: bytes) -> Dict[str, Track]:
    """The named tracks of a standard MIDI file, with every time in seconds through its tempo map.

    Args:
        data: The file's bytes.

    Returns:
        Dict[str, Track]: Each track by the name its name event gives, in file order.

    Raises:
        MidiFormatError: If the bytes hold no MIDI header, or time in SMPTE frames.
    """
    if data[:4] != HEADER_CHUNK:
        raise MidiFormatError("The data holds no MIDI header")

    division = int.from_bytes(data[12:14], "big")
    if division & SMPTE_BIT:
        raise MidiFormatError("The file counts time in SMPTE frames, and this reader counts beats")

    position = 8 + int.from_bytes(data[4:8], "big")
    named: List[Tuple[str, List[Event]]] = []
    tempos: List[Tuple[int, int]] = []
    while data[position : position + 4] == TRACK_CHUNK:
        length = int.from_bytes(data[position + 4 : position + 8], "big")
        name, events = _read_track(data[position + 8 : position + 8 + length], tempos)
        named.append((name, events))
        position += 8 + length

    seconds = _clock(sorted(tempos), division)
    return {name: _track(events, seconds) for name, events in named}


def _read_track(data: bytes, tempos: List[Tuple[int, int]]) -> Tuple[str, List[Event]]:
    """A track's name and its channel events, noting every tempo change it holds in ``tempos``."""
    position, tick, status, name = 0, 0, 0, ""
    events: List[Event] = []
    while position < len(data):
        delta, position = _variable_length(data, position)
        tick += delta
        byte = data[position]
        if byte == META_EVENT:
            kind = data[position + 1]
            size, position = _variable_length(data, position + 2)
            payload = data[position : position + size]
            position += size
            if kind == TRACK_NAME:
                name = payload.decode("latin-1")
            elif kind == SET_TEMPO:
                tempos.append((tick, int.from_bytes(payload, "big")))
            continue

        if byte in SYSEX_EVENTS:
            size, position = _variable_length(data, position + 1)
            position += size
            continue

        if byte & STATUS_BIT:
            status = byte
            position += 1

        if status & 0xF0 in ONE_BYTE_MESSAGES:
            position += 1
            continue

        events.append(Event(tick=tick, status=status & 0xF0, first=data[position], second=data[position + 1]))
        position += 2

    return name, events


def _variable_length(data: bytes, position: int) -> Tuple[int, int]:
    value = 0
    while True:
        byte = data[position]
        position += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & STATUS_BIT:
            return value, position


def _clock(tempos: List[Tuple[int, int]], division: int) -> List[Tuple[int, float, float]]:
    """The tempo map as (tick, seconds at that tick, microseconds per tick from it on)."""
    clock: List[Tuple[int, float, float]] = [(0, 0.0, DEFAULT_TEMPO / division)]
    for tick, tempo in tempos:
        last_tick, last_seconds, per_tick = clock[-1]
        clock.append((tick, last_seconds + (tick - last_tick) * per_tick / MICROSECONDS, tempo / division))

    return clock


def _seconds(clock: List[Tuple[int, float, float]], tick: int) -> float:
    start, seconds, per_tick = next(entry for entry in reversed(clock) if entry[0] <= tick)
    return seconds + (tick - start) * per_tick / MICROSECONDS


def _track(events: List[Event], clock: List[Tuple[int, float, float]]) -> Track:
    track = Track()
    open_notes: Dict[int, Tuple[float, int]] = {}
    for event in events:
        time = _seconds(clock, event.tick)
        if event.status == NOTE_ON and event.second > 0:
            open_notes[event.first] = (time, event.second)
        elif event.status in (NOTE_OFF, NOTE_ON):
            opened = open_notes.pop(event.first, None)
            if opened is not None:
                track.notes.append(Note(start=opened[0], end=time, pitch=event.first, velocity=opened[1]))
        elif event.status == CONTROL_CHANGE:
            track.controllers.setdefault(event.first, []).append((time, event.second))

    track.notes.sort(key=lambda note: note.start)
    return track
