from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Self, Tuple

HEADER_CHUNK: Final[bytes] = b"MThd"
TRACK_CHUNK: Final[bytes] = b"MTrk"
CHUNK_TYPE_BYTES: Final[int] = 4
CHUNK_PREFIX_BYTES: Final[int] = 8
DIVISION_START: Final[int] = 12
DIVISION_END: Final[int] = 14
META_EVENT: Final[int] = 0xFF
SYSEX_EVENTS: Final[Tuple[int, int]] = (0xF0, 0xF7)
TRACK_NAME: Final[int] = 0x03
SET_TEMPO: Final[int] = 0x51
NOTE_OFF: Final[int] = 0x80
NOTE_ON: Final[int] = 0x90
NOTE_EVENTS: Final[Tuple[int, int]] = (NOTE_OFF, NOTE_ON)
CONTROL_CHANGE: Final[int] = 0xB0
ONE_BYTE_MESSAGES: Final[Tuple[int, int]] = (0xC0, 0xD0)
STATUS_BIT: Final[int] = 0x80
MESSAGE_KIND_MASK: Final[int] = 0xF0
CONTINUATION_BIT: Final[int] = 0x80
SEVEN_BITS: Final[int] = 0x7F
BITS_PER_GROUP: Final[int] = 7
SMPTE_BIT: Final[int] = 0x8000
DEFAULT_TEMPO: Final[int] = 500_000
MICROSECONDS: Final[float] = 1e6
TRACK_NAME_ENCODING: Final[str] = "latin-1"


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
    """A channel message at the tick it falls on: its kind with the channel masked off, and its two data bytes."""

    tick: int
    status: int
    first: int
    second: int


@dataclass(frozen=True)
class TempoSpan:
    """A stretch of the piece at one tempo, from the tick a tempo is set at.

    Attributes:
        tick: The tick the stretch starts at.
        seconds: The time in seconds at that tick.
        microseconds_per_tick: How long each tick of the stretch lasts.
    """

    tick: int
    seconds: float
    microseconds_per_tick: float


class TempoMap:
    """The piece's clock: the time in seconds at every tick, through each tempo the piece sets.

    The piece plays at the MIDI default tempo until its first tempo change. Every tempo set in any
    track holds for the whole piece, as a file of tracks playing together keeps one tempo map. The
    tempos are ordered by the tick they are set at, and tempos set at one tick keep the order the file
    gives them, so the last of them holds from that tick on.
    """

    def __init__(self, tempos: List[Tuple[int, int]], division: int) -> None:
        spans = [TempoSpan(tick=0, seconds=0.0, microseconds_per_tick=DEFAULT_TEMPO / division)]
        for tick, tempo in sorted(tempos, key=_tempo_tick):
            last = spans[-1]
            seconds = last.seconds + (tick - last.tick) * last.microseconds_per_tick / MICROSECONDS
            spans.append(TempoSpan(tick=tick, seconds=seconds, microseconds_per_tick=tempo / division))

        self._spans = spans

    def seconds_at(self, tick: int) -> float:
        """The time in seconds at ``tick``, from the last tempo set by then."""
        span = next(span for span in reversed(self._spans) if span.tick <= tick)
        return span.seconds + (tick - span.tick) * span.microseconds_per_tick / MICROSECONDS


class TrackReader:
    """Reads one track chunk: its name, its channel messages and the tempos it sets, in order.

    A channel message may leave out its status byte where it repeats the one before (running status),
    so the reader keeps the last status between messages. Meta events give the track's name and the
    tempo, and system-exclusive events are skipped.

    Attributes:
        name: The track's name, as its name event gives it, empty before one.
        events: Its channel messages of two data bytes, in order.
        tempos: Each tempo it sets, as the tick beside the microseconds per beat.
    """

    def __init__(self, data: bytes) -> None:
        self.name = ""
        self.events: List[Event] = []
        self.tempos: List[Tuple[int, int]] = []
        self._data = data
        self._position = 0
        self._tick = 0
        self._status = 0

    def read(self) -> Self:
        """Reads every event of the chunk."""
        while self._position < len(self._data):
            delta, self._position = _variable_length(self._data, self._position)
            self._tick += delta
            byte = self._data[self._position]
            if byte == META_EVENT:
                self._read_meta()
            elif byte in SYSEX_EVENTS:
                self._skip_sysex()
            else:
                self._read_channel_message(byte)

        return self

    def _read_meta(self) -> None:
        """A meta event: its kind, then its length and payload; the name and the tempo are kept."""
        kind = self._data[self._position + 1]
        size, self._position = _variable_length(self._data, self._position + 2)
        payload = self._data[self._position : self._position + size]
        self._position += size
        if kind == TRACK_NAME:
            self.name = payload.decode(TRACK_NAME_ENCODING)
        elif kind == SET_TEMPO:
            self.tempos.append((self._tick, int.from_bytes(payload, "big")))

    def _skip_sysex(self) -> None:
        """A system-exclusive event: its length, then a payload left unread."""
        size, self._position = _variable_length(self._data, self._position + 1)
        self._position += size

    def _read_channel_message(self, byte: int) -> None:
        """A channel message under its own status byte, or, under running status, under the last one."""
        if byte & STATUS_BIT:
            self._status = byte
            self._position += 1

        if self._status & MESSAGE_KIND_MASK in ONE_BYTE_MESSAGES:
            self._position += 1
            return

        self.events.append(
            Event(
                tick=self._tick,
                status=self._status & MESSAGE_KIND_MASK,
                first=self._data[self._position],
                second=self._data[self._position + 1],
            )
        )
        self._position += 2


def read_midi(data: bytes) -> Dict[str, Track]:
    """The named tracks of a standard MIDI file, with every time in seconds through its tempo map.

    The header chunk holds the time division at bytes 12 and 13, and the track chunks follow it, each
    a type and a length before its events.

    Args:
        data: The file's bytes.

    Returns:
        Dict[str, Track]: Each track by the name its name event gives, in file order.

    Raises:
        MidiFormatError: If the bytes hold no MIDI header, or time in SMPTE frames.
    """
    if data[:CHUNK_TYPE_BYTES] != HEADER_CHUNK:
        raise MidiFormatError("The data holds no MIDI header")

    division = int.from_bytes(data[DIVISION_START:DIVISION_END], "big")
    if division & SMPTE_BIT:
        raise MidiFormatError("The file counts time in SMPTE frames, and this reader counts beats")

    readers = [TrackReader(chunk).read() for chunk in _track_chunks(data)]
    clock = TempoMap([tempo for reader in readers for tempo in reader.tempos], division)
    return {reader.name: _track(reader.events, clock) for reader in readers}


def _track_chunks(data: bytes) -> List[bytes]:
    """The body of every track chunk after the header chunk, in file order."""
    position = CHUNK_PREFIX_BYTES + _chunk_length(data, 0)
    chunks: List[bytes] = []
    while data[position : position + CHUNK_TYPE_BYTES] == TRACK_CHUNK:
        length = _chunk_length(data, position)
        chunks.append(data[position + CHUNK_PREFIX_BYTES : position + CHUNK_PREFIX_BYTES + length])
        position += CHUNK_PREFIX_BYTES + length

    return chunks


def _tempo_tick(tempo: Tuple[int, int]) -> int:
    """The tick a tempo is set at, which orders the tempo map."""
    tick, _ = tempo
    return tick


def _chunk_length(data: bytes, position: int) -> int:
    """The length of the chunk starting at ``position``, which follows its type."""
    return int.from_bytes(data[position + CHUNK_TYPE_BYTES : position + CHUNK_PREFIX_BYTES], "big")


def _variable_length(data: bytes, position: int) -> Tuple[int, int]:
    """The variable-length quantity at ``position``, and the position after it.

    Each byte gives seven bits of the value, most significant first, and every byte but the last
    sets its continuation bit.
    """
    value = 0
    while True:
        byte = data[position]
        position += 1
        value = (value << BITS_PER_GROUP) | (byte & SEVEN_BITS)
        if not byte & CONTINUATION_BIT:
            return value, position


def _track(events: List[Event], clock: TempoMap) -> Track:
    """The notes and controller values ``events`` play, in seconds.

    Every note event ends the note sounding at its pitch: a note off, a note on of velocity zero, and
    a note on striking the pitch again, which then starts the new note. A note struck again while it
    sounds therefore plays twice, the first time up to the new strike.
    """
    track = Track()
    open_notes: Dict[int, Tuple[float, int]] = {}
    for event in events:
        time = clock.seconds_at(event.tick)
        if event.status in NOTE_EVENTS:
            closed = _closed(open_notes, event.first, time)
            if closed is not None:
                track.notes.append(closed)

            if event.status == NOTE_ON and event.second > 0:
                open_notes[event.first] = (time, event.second)
        elif event.status == CONTROL_CHANGE:
            track.controllers.setdefault(event.first, []).append((time, event.second))

    track.notes.sort(key=lambda note: note.start)
    return track


def _closed(open_notes: Dict[int, Tuple[float, int]], pitch: int, time: float) -> Optional[Note]:
    """The note open at ``pitch``, taken out of ``open_notes`` and ended at ``time``.

    Returns ``None`` where no note is open at ``pitch``, or where the note would end where it starts,
    since a note lasting no time plays nothing.
    """
    opened = open_notes.pop(pitch, None)
    if opened is None:
        return None

    start, velocity = opened
    if time <= start:
        return None

    return Note(start=start, end=time, pitch=pitch, velocity=velocity)
