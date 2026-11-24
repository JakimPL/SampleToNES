from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, Dict, Final, List, Tuple, Type

if TYPE_CHECKING:
    from pretty_midi import ControlChange, Instrument
    from pretty_midi import Note as PrettyMidiNote
    from pretty_midi import PrettyMIDI

MALFORMED_FILE_ERRORS: Final[Tuple[Type[Exception], ...]] = (
    EOFError,
    IndexError,
    OSError,
    ValueError,
    ZeroDivisionError,
)
LONGEST_FILE_TICKS: Final[int] = 100_000_000

Controllers = Dict[int, List[Tuple[float, int]]]


class MidiFormatError(ValueError):
    """Raised when bytes hold no standard MIDI file pretty_midi reads."""


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


@dataclass(frozen=True)
class Track:
    """What one named track plays, in seconds.

    Attributes:
        notes: Its notes, ordered by their start.
        controllers: Each controller's values by its number, each beside the time it is set, in order.
    """

    notes: List[Note]
    controllers: Controllers


def read_midi(data: bytes) -> Dict[str, Track]:
    """The named tracks of a standard MIDI file, as pretty_midi reads them, with every time in seconds.

    pretty_midi times every track through the tempo map the file's first track sets, at 120 beats a
    minute until its first tempo. Where tempos share a tick, the last the file sets holds. A release
    ends every note of its pitch struck at an earlier tick, so a note struck again while it sounds
    plays twice, both strikes lasting to the release. A note struck at the tick of a release that
    ends an earlier note of its pitch starts there. A note released at the tick it is struck, or
    never released, is left out.

    pretty_midi gives an instrument for each program and channel a track plays, named after the
    track, and the reader gathers them back into the track. A file spanning more than
    ``LONGEST_FILE_TICKS`` ticks is refused.

    Args:
        data: The file's bytes.

    Returns:
        Dict[str, Track]: Each track that plays a note, by the name its name event gives, in file order.

    Raises:
        MidiFormatError: If pretty_midi reads no MIDI file in the bytes, or the file spans more ticks than the limit.
    """
    midi = _parsed(data)
    names = dict.fromkeys(instrument.name for instrument in midi.instruments)
    return {name: _track([item for item in midi.instruments if item.name == name]) for name in names}


def _parsed(data: bytes) -> PrettyMIDI:
    """The file pretty_midi reads from ``data``.

    pretty_midi and mido come with the development and ``calibration`` dependency groups, which an
    installed copy leaves to its owner, and that copy's calibration command imports this module on
    every run, so both are imported here, where a file is read.

    pretty_midi keeps the time of every tick a file spans, and refuses a file spanning more ticks
    than its module-level ``MAX_TICK`` as likely corrupt. Its own limit of ten million ticks holds
    under four minutes at the 44,100 ticks a second NES-MDB counts, and the longest piece of
    NES-MDB spans about 67 million. The reader sets the limit to ``LONGEST_FILE_TICKS``, which
    reads every piece of NES-MDB and keeps the clock of a file at the limit to 800 MB.

    mido, which pretty_midi parses the file with, raises a ``KeySignatureError`` of its own on a key
    signature naming no key, and the reader refuses it with the other failures of a malformed file.

    Raises:
        MidiFormatError: If pretty_midi reads no MIDI file in the bytes, or the file spans more ticks than the limit.
    """
    import mido
    import pretty_midi

    pretty_midi.pretty_midi.MAX_TICK = LONGEST_FILE_TICKS
    try:
        midi = pretty_midi.PrettyMIDI(BytesIO(data))
    except (*MALFORMED_FILE_ERRORS, mido.KeySignatureError) as error:
        raise MidiFormatError(f"pretty_midi reads no MIDI file in the data: {error}") from error

    return midi


def _track(instruments: List[Instrument]) -> Track:
    """The notes and controller values of one track's instruments, each kept once and ordered by time.

    pretty_midi hands the control changes a track sets before its first note to every instrument
    the track makes afterwards, as one shared list, so the reader keeps each change once, by its
    identity.
    """
    notes = [_note(note) for instrument in instruments for note in instrument.notes]
    changes = dict.fromkeys(change for instrument in instruments for change in instrument.control_changes)
    controllers: Controllers = {}
    for change in sorted(changes, key=_change_time):
        controllers.setdefault(int(change.number), []).append((float(change.time), int(change.value)))

    return Track(notes=sorted(notes, key=_note_start), controllers=controllers)


def _note(note: PrettyMidiNote) -> Note:
    """One of pretty_midi's notes, its times as plain seconds."""
    return Note(start=float(note.start), end=float(note.end), pitch=int(note.pitch), velocity=int(note.velocity))


def _note_start(note: Note) -> float:
    """When a note starts, which orders a track's notes."""
    return note.start


def _change_time(change: ControlChange) -> float:
    """When a control change is set, which orders a track's controller values."""
    return float(change.time)
