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
BITPHASE_DEFAULT_EFFECT: Final[int] = 0
BITPHASE_DEFAULT_EFFECT_DELAY: Final[int] = 0
BITPHASE_DEFAULT_EFFECT_PARAMETER: Final[int] = 0
BITPHASE_FIRST_TABLE_INDEX: Final[int] = 0
BITPHASE_NO_EFFECTS: Final[Tuple[None, ...]] = (None,)
BITPHASE_MIN_EFFECT_COLUMNS: Final[int] = 1
BITPHASE_MAX_EFFECT_COLUMNS: Final[int] = 4
BITPHASE_DEFAULT_INSTRUMENT_ID: Final[str] = "01"
BITPHASE_DEFAULT_LOOP: Final[int] = 0
BITPHASE_DEFAULT_TABLE_ID: Final[int] = 0
BITPHASE_MAX_MACRO_LENGTH: Final[int] = 512
BITPHASE_MACRO_DEFAULTS: Final[Dict[str, Any]] = {
    "pulseWidth": 2,
    "volumeOrRate": 15,
    "envelope": False,
    "retrigger": False,
    "soundLength": 0,
    "toneAdd": 0,
    "toneAccumulation": False,
    "sweep": False,
    "sweepRate": 0,
    "sweepShift": 0,
}

MIN_INITIAL_SPEED: Final[int] = 1
MAX_INITIAL_SPEED: Final[int] = 255
MIN_PATTERN_LENGTH: Final[int] = 1
MAX_PATTERN_LENGTH: Final[int] = 256


@dataclass(frozen=True)
class LoadedNote:
    name: int
    octave: int


@dataclass(frozen=True)
class LoadedEffect:
    effect: int
    delay: int
    parameter: int
    table_index: Optional[int]


@dataclass(frozen=True)
class LoadedRow:
    note: LoadedNote
    effects: List[Optional[LoadedEffect]]
    instrument: int
    table: int
    volume: int


@dataclass(frozen=True)
class LoadedChannel:
    label: str
    rows: List[LoadedRow]
    effect_column_count: int


@dataclass(frozen=True)
class LoadedPattern:
    id: int
    length: int
    channels: List[LoadedChannel]


@dataclass(frozen=True)
class LoadedMacro:
    values: List[Any]
    loop: int


@dataclass(frozen=True)
class LoadedInstrument:
    id: str
    chip_type: str
    name: str
    macros: Dict[str, LoadedMacro]

    @property
    def number(self) -> int:
        """The value a pattern's instrument column carries to play this instrument."""
        return int(self.id, 36)

    def macro(self, field: str) -> LoadedMacro:
        """The macro Bitphase reads a field from, which one the instrument leaves out defaults.

        Args:
            field: The instrument field, named as Bitphase keys it.

        Returns:
            LoadedMacro: The field's own macro, or the single default value it takes.
        """
        return self.macros.get(field, LoadedMacro(values=[BITPHASE_MACRO_DEFAULTS[field]], loop=0))


@dataclass(frozen=True)
class LoadedTable:
    id: int
    loop: int
    name: str
    rows: List[int]
    additive: bool


@dataclass(frozen=True)
class LoadedSong:
    chip_type: Optional[str]
    chip_variant: str
    chip_frequency: Optional[int]
    interrupt_frequency: int
    a4_tuning_hz: float
    initial_speed: int
    default_pattern_length: int
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


def _table_index(data: Dict[str, Any]) -> Optional[int]:
    """The table an effect reads, which Bitphase takes from any index of zero or above.

    A cell stating no index at all is driven by its own parameter, and one carrying an
    empty value reads as the first table, since that is what the comparison Bitphase
    makes says of it.
    """
    if "tableIndex" not in data:
        return None

    index = data["tableIndex"]
    if index is None:
        return BITPHASE_FIRST_TABLE_INDEX

    return index if index >= BITPHASE_FIRST_TABLE_INDEX else None


def _effect(data: Optional[Dict[str, Any]]) -> Optional[LoadedEffect]:
    if data is None:
        return None

    return LoadedEffect(
        effect=data.get("effect", BITPHASE_DEFAULT_EFFECT),
        delay=data.get("delay", BITPHASE_DEFAULT_EFFECT_DELAY),
        parameter=data.get("parameter", BITPHASE_DEFAULT_EFFECT_PARAMETER),
        table_index=_table_index(data),
    )


def _effects(data: Optional[List[Optional[Dict[str, Any]]]]) -> List[Optional[LoadedEffect]]:
    """One entry per effect column, which a row naming none reaches playback holding empty."""
    if not data:
        return list(BITPHASE_NO_EFFECTS)

    return [_effect(entry) for entry in data]


def _row(data: Dict[str, Any]) -> LoadedRow:
    return LoadedRow(
        note=_note(data.get("note")),
        effects=_effects(data.get("effects")),
        instrument=data.get("instrument", BITPHASE_DEFAULT_INSTRUMENT),
        table=data.get("table", BITPHASE_DEFAULT_TABLE),
        volume=data.get("volume", BITPHASE_DEFAULT_VOLUME),
    )


def _effect_column_count(data: Dict[str, Any], rows: List[LoadedRow]) -> int:
    """How many effect columns a channel lays out, which its widest line states.

    Bitphase takes the count the channel carries where it holds one, and reads it off the
    lines otherwise, so a channel written without the field lays out as many columns as its
    lines fill.
    """
    stated = data.get("effectColumnCount")
    if isinstance(stated, int):
        return min(max(stated, BITPHASE_MIN_EFFECT_COLUMNS), BITPHASE_MAX_EFFECT_COLUMNS)

    return max(
        (len(row.effects) for row in rows),
        default=BITPHASE_MIN_EFFECT_COLUMNS,
    )


def _channel(data: Dict[str, Any], label: str) -> LoadedChannel:
    rows = [_row(row) for row in data.get("rows") or []]
    return LoadedChannel(
        label=label,
        rows=rows,
        effect_column_count=_effect_column_count(data, rows),
    )


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


def _macro(data: Dict[str, Any]) -> LoadedMacro:
    """One macro as Bitphase resolves it, within the values it stores and the loop they hold."""
    values = list(data.get("values") or [])[:BITPHASE_MAX_MACRO_LENGTH]
    loop = data.get("loop", BITPHASE_DEFAULT_LOOP)
    return LoadedMacro(values=values, loop=min(max(loop, 0), max(len(values) - 1, 0)))


def _macros(data: Dict[str, Any]) -> Dict[str, LoadedMacro]:
    macros = data.get("macros") or {}
    return {field: _macro(macro) for field, macro in macros.items()}


def _instrument(data: Dict[str, Any]) -> LoadedInstrument:
    identifier = data.get("id")
    chip_type = data.get("chipType")
    return LoadedInstrument(
        id=identifier if isinstance(identifier, str) else BITPHASE_DEFAULT_INSTRUMENT_ID,
        chip_type=chip_type if isinstance(chip_type, str) else BITPHASE_DEFAULT_CHIP_TYPE,
        name=data.get("name", BITPHASE_DEFAULT_NAME),
        macros=_macros(data),
    )


def _table(data: Dict[str, Any]) -> LoadedTable:
    return LoadedTable(
        id=data.get("id", BITPHASE_DEFAULT_TABLE_ID),
        loop=data.get("loop", BITPHASE_DEFAULT_LOOP),
        name=data.get("name", BITPHASE_DEFAULT_NAME),
        rows=list(data.get("rows") or []),
        additive=bool(data.get("additive", False)),
    )


def _initial_speed(data: Dict[str, Any]) -> int:
    speed = data.get("initialSpeed")
    if isinstance(speed, int) and MIN_INITIAL_SPEED <= speed <= MAX_INITIAL_SPEED:
        return speed

    return BITPHASE_DEFAULT_INITIAL_SPEED


def _default_pattern_length(data: Dict[str, Any]) -> int:
    """The line count a pattern added to the song takes, within the range Bitphase keeps."""
    length = data.get("defaultPatternLength")
    if isinstance(length, int) and MIN_PATTERN_LENGTH <= length <= MAX_PATTERN_LENGTH:
        return length

    return BITPHASE_DEFAULT_PATTERN_LENGTH


def _song(data: Dict[str, Any], labels: List[str]) -> LoadedSong:
    return LoadedSong(
        chip_type=data.get("chipType"),
        chip_variant=data.get("chipVariant", BITPHASE_DEFAULT_CHIP_VARIANT),
        chip_frequency=data.get("chipFrequency"),
        interrupt_frequency=data.get("interruptFrequency", BITPHASE_DEFAULT_INTERRUPT_FREQUENCY),
        a4_tuning_hz=data.get("a4TuningHz", BITPHASE_DEFAULT_A4_TUNING),
        initial_speed=_initial_speed(data),
        default_pattern_length=_default_pattern_length(data),
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
