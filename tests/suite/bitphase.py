import gzip
import json
from dataclasses import dataclass
from typing import Any, Dict, Final, List, Optional, Tuple

BITPHASE_DEFAULT_NAME: Final[str] = ""
BITPHASE_DEFAULT_AUTHOR: Final[str] = ""
BITPHASE_DEFAULT_LOOP_POINT: Final[int] = 0
BITPHASE_DEFAULT_PATTERN_ORDER: Final[Tuple[int, ...]] = (0,)
BITPHASE_DEFAULT_PATTERN_LENGTH: Final[int] = 64
BITPHASE_DEFAULT_ROW_COUNT: Final[int] = 64
BITPHASE_DEFAULT_INTERRUPT_FREQUENCY: Final[int] = 50
BITPHASE_DEFAULT_INITIAL_SPEED: Final[int] = 3
BITPHASE_DEFAULT_CHIP_VARIANT: Final[str] = "NTSC"
BITPHASE_DEFAULT_A4_TUNING: Final[float] = 440.0
BITPHASE_DEFAULT_CHIP_TYPE: Final[str] = "ay"
BITPHASE_DEFAULT_NOTE_NAME: Final[int] = 0
BITPHASE_DEFAULT_OCTAVE: Final[int] = 0
BITPHASE_DEFAULT_INSTRUMENT: Final[int] = 0
BITPHASE_DEFAULT_TABLE: Final[int] = 0
BITPHASE_DEFAULT_VOLUME: Final[int] = 0
BITPHASE_DEFAULT_INSTRUMENT_ID: Final[str] = "01"
BITPHASE_DEFAULT_LOOP: Final[int] = 0
BITPHASE_DEFAULT_TABLE_ID: Final[int] = 0
BITPHASE_DEFAULT_PULSE_WIDTH: Final[int] = 2
BITPHASE_DEFAULT_VOLUME_OR_RATE: Final[int] = 15

MIN_INITIAL_SPEED: Final[int] = 1
MAX_INITIAL_SPEED: Final[int] = 255


@dataclass(frozen=True)
class LoadedNote:
    name: int
    octave: int


@dataclass(frozen=True)
class LoadedRow:
    note: LoadedNote
    instrument: int
    table: int
    volume: int


@dataclass(frozen=True)
class LoadedChannel:
    label: str
    rows: List[LoadedRow]


@dataclass(frozen=True)
class LoadedPattern:
    id: int
    length: int
    channels: List[LoadedChannel]


@dataclass(frozen=True)
class LoadedInstrumentRow:
    pulse_width: int
    volume_or_rate: int
    envelope: bool
    sound_length: int
    tone_add: int
    tone_accumulation: bool
    retrigger: bool
    sweep: bool
    sweep_rate: int
    sweep_shift: int


@dataclass(frozen=True)
class LoadedInstrument:
    id: str
    chip_type: str
    loop: int
    name: str
    rows: List[LoadedInstrumentRow]

    @property
    def number(self) -> int:
        """The value a pattern's instrument column carries to play this instrument."""
        return int(self.id, 36)


@dataclass(frozen=True)
class LoadedTable:
    id: int
    loop: int
    name: str
    rows: List[int]


@dataclass(frozen=True)
class LoadedSong:
    chip_type: Optional[str]
    chip_variant: str
    chip_frequency: Optional[int]
    interrupt_frequency: int
    a4_tuning_hz: float
    initial_speed: int
    tuning_table: List[int]
    patterns: List[LoadedPattern]


@dataclass(frozen=True)
class LoadedProject:
    name: str
    author: str
    loop_point_id: int
    pattern_order: List[int]
    songs: List[LoadedSong]
    tables: List[LoadedTable]
    instruments: List[LoadedInstrument]


def _note(data: Optional[Dict[str, Any]]) -> LoadedNote:
    source = data or {}
    return LoadedNote(
        name=source.get("name", BITPHASE_DEFAULT_NOTE_NAME),
        octave=source.get("octave", BITPHASE_DEFAULT_OCTAVE),
    )


def _row(data: Dict[str, Any]) -> LoadedRow:
    return LoadedRow(
        note=_note(data.get("note")),
        instrument=data.get("instrument", BITPHASE_DEFAULT_INSTRUMENT),
        table=data.get("table", BITPHASE_DEFAULT_TABLE),
        volume=data.get("volume", BITPHASE_DEFAULT_VOLUME),
    )


def _channel(data: Dict[str, Any], label: str) -> LoadedChannel:
    rows = data.get("rows")
    if rows is None:
        return LoadedChannel(label=label, rows=[])

    return LoadedChannel(label=label, rows=[_row(row) for row in rows])


def _pattern(data: Dict[str, Any], labels: List[str]) -> LoadedPattern:
    channels = data.get("channels") or []
    return LoadedPattern(
        id=data.get("id", 0),
        length=data.get("length", BITPHASE_DEFAULT_PATTERN_LENGTH),
        channels=[
            _channel(channel, labels[index] if index < len(labels) else chr(ord("A") + index))
            for index, channel in enumerate(channels)
        ],
    )


def _instrument_row(data: Dict[str, Any]) -> LoadedInstrumentRow:
    return LoadedInstrumentRow(
        pulse_width=data.get("pulseWidth", BITPHASE_DEFAULT_PULSE_WIDTH),
        volume_or_rate=data.get("volumeOrRate", BITPHASE_DEFAULT_VOLUME_OR_RATE),
        envelope=bool(data.get("envelope", False)),
        sound_length=data.get("soundLength", 0),
        tone_add=data.get("toneAdd", 0),
        tone_accumulation=bool(data.get("toneAccumulation", False)),
        retrigger=bool(data.get("retrigger", False)),
        sweep=bool(data.get("sweep", False)),
        sweep_rate=data.get("sweepRate", 0),
        sweep_shift=data.get("sweepShift", 0),
    )


def _instrument(data: Dict[str, Any]) -> LoadedInstrument:
    identifier = data.get("id")
    chip_type = data.get("chipType")
    return LoadedInstrument(
        id=identifier if isinstance(identifier, str) else BITPHASE_DEFAULT_INSTRUMENT_ID,
        chip_type=chip_type if isinstance(chip_type, str) else BITPHASE_DEFAULT_CHIP_TYPE,
        loop=data.get("loop", BITPHASE_DEFAULT_LOOP),
        name=data.get("name", BITPHASE_DEFAULT_NAME),
        rows=[_instrument_row(row) for row in data.get("rows") or []],
    )


def _table(data: Dict[str, Any]) -> LoadedTable:
    return LoadedTable(
        id=data.get("id", BITPHASE_DEFAULT_TABLE_ID),
        loop=data.get("loop", BITPHASE_DEFAULT_LOOP),
        name=data.get("name", BITPHASE_DEFAULT_NAME),
        rows=list(data.get("rows") or []),
    )


def _initial_speed(data: Dict[str, Any]) -> int:
    speed = data.get("initialSpeed")
    if isinstance(speed, int) and MIN_INITIAL_SPEED <= speed <= MAX_INITIAL_SPEED:
        return speed

    return BITPHASE_DEFAULT_INITIAL_SPEED


def _song(data: Dict[str, Any], labels: List[str]) -> LoadedSong:
    return LoadedSong(
        chip_type=data.get("chipType"),
        chip_variant=data.get("chipVariant", BITPHASE_DEFAULT_CHIP_VARIANT),
        chip_frequency=data.get("chipFrequency"),
        interrupt_frequency=data.get("interruptFrequency", BITPHASE_DEFAULT_INTERRUPT_FREQUENCY),
        a4_tuning_hz=data.get("a4TuningHz", BITPHASE_DEFAULT_A4_TUNING),
        initial_speed=_initial_speed(data),
        tuning_table=list(data.get("tuningTable") or []),
        patterns=[_pattern(pattern, labels) for pattern in data.get("patterns") or []],
    )


def parse_btp(data: bytes, channel_labels: List[str]) -> LoadedProject:
    """Reads a ``.btp`` the way Bitphase's project loader does.

    The loader takes each field on its own and falls back to a default for any it
    misses, so reading a document through the same fallbacks turns a field left out
    into the default value the assertion catches.

    Args:
        data: The file's contents.
        channel_labels: Channel names the chip schema supplies, which the loader
            assigns to a pattern's channels by position.

    Returns:
        LoadedProject: The document as Bitphase reconstructs it.
    """
    document: Dict[str, Any] = json.loads(gzip.decompress(data))
    return LoadedProject(
        name=document.get("name", BITPHASE_DEFAULT_NAME),
        author=document.get("author", BITPHASE_DEFAULT_AUTHOR),
        loop_point_id=document.get("loopPointId", BITPHASE_DEFAULT_LOOP_POINT),
        pattern_order=list(document.get("patternOrder") or BITPHASE_DEFAULT_PATTERN_ORDER),
        songs=[_song(song, channel_labels) for song in document.get("songs") or []],
        tables=[_table(table) for table in document.get("tables") or []],
        instruments=[_instrument(instrument) for instrument in document.get("instruments") or []],
    )
