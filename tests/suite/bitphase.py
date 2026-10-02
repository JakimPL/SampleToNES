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
BITPHASE_SILENT_PERIOD: Final[int] = 0
BITPHASE_MAX_PERIOD: Final[int] = 2047
BITPHASE_OPENING_PATTERN_VOLUME: Final[int] = 15
BITPHASE_STORED_VOLUME_OFF: Final[int] = -1
BITPHASE_SILENCED_PATTERN_VOLUME: Final[int] = 0
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

BITPHASE_NOISE_PERIOD_COUNT: Final[int] = 16
BITPHASE_NOTE_OFF: Final[int] = 1
BITPHASE_NO_NOTE: Final[int] = 0
BITPHASE_FIRST_NOTE_NAME: Final[int] = 2
BITPHASE_NOTE_RANGE: Final[int] = 12
BITPHASE_FIRST_OCTAVE: Final[int] = 1
BITPHASE_TABLE_OFF: Final[int] = -1
BITPHASE_TABLE_COLUMN_OFFSET: Final[int] = 1
BITPHASE_ORNAMENT_POSITION: Final[int] = 5
BITPHASE_ORNAMENT_POSITION_MASK: Final[int] = 0xFF
BITPHASE_SPEED_EFFECT: Final[int] = ord("S")
BITPHASE_FIRST_STEP: Final[int] = 0
BITPHASE_NOISE_TIMERS: Final[Tuple[int, ...]] = (
    4,
    8,
    16,
    32,
    64,
    96,
    128,
    160,
    202,
    254,
    380,
    508,
    762,
    1016,
    2034,
    4068,
)

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

    def value(self, field: str, tick: int) -> Any:
        """The value a field takes on a tick of a sounding note.

        Args:
            field: The instrument field, named as Bitphase keys it.
            tick: Ticks since the note started.

        Returns:
            Any: The value the engine samples for that field.
        """
        macro = self.macro(field)
        return macro.values[sample_index(tick, len(macro.values), macro.loop)]


@dataclass(frozen=True)
class LoadedTable:
    id: int
    loop: int
    name: str
    rows: List[int]
    additive: bool

    def step(self, tick: int) -> int:
        """The semitone step the table moves the note by on a tick of a sounding note."""
        return self.rows[sample_index(tick, len(self.rows), self.loop)]


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


def sample_index(tick: int, length: int, loop: int) -> int:
    """The index a per-tick list stands at on a tick, as Bitphase's engine advances it.

    An instrument macro and a table each advance one entry per tick and circle once they run
    out, from the loop entry where it stands among them and from the first otherwise. Read from
    ``sampleInstrumentMacroIndex`` and ``processTables`` of the tracker at commit ``265ff70``.

    Args:
        tick: Ticks since the note started.
        length: Entries the list holds.
        loop: Entry the list circles from.

    Returns:
        int: The entry to read.
    """
    entries = length if length > 0 else 1
    if tick < entries:
        return max(tick, 0)

    start = loop if 0 < loop < entries else 0
    span = entries - start
    if span <= 0:
        return entries - 1

    return start + (tick - entries) % span


def sounded_period(
    tuning_table: List[int],
    note_index: int,
    instrument: LoadedInstrument,
    table: LoadedTable,
    tick: int,
) -> int:
    """The channel period a tone channel sounds on a tick, as the engine resolves it.

    The table moves the note, the tuning table resolves the period that note sounds at, and the
    instrument's tone offset moves it from there. Read from ``nes-audio-driver.js`` of the
    tracker at commit ``265ff70``, where a period of zero silences the channel.

    Args:
        tuning_table: The song's period per note index.
        note_index: The note the pattern cell names.
        instrument: The instrument the cell triggers.
        table: The table the cell attaches.
        tick: Ticks since the note started.

    Returns:
        int: The period the channel holds, within the timer's range.
    """
    moved = reached_note(tuning_table, note_index, table, tick)
    period = tuning_table[moved] + int(instrument.value("toneAdd", tick))
    return min(max(period, BITPHASE_SILENT_PERIOD), BITPHASE_MAX_PERIOD)


def noise_register(note_index: int) -> int:
    """The period register value the noise channel writes for the note it reaches, as the engine resolves it.

    The driver counts the note index down from the top of each cycle of sixteen, and the register
    selects the timer from ``BITPHASE_NOISE_TIMERS``, the NTSC table fastest first. Read from
    ``resolveNesNoisePeriodFromSemitoneOffset`` of ``nes-audio-driver.js``, the ``$400E`` write of
    ``nes-apu-engine.js`` and ``wavlen_table`` of ``nsfplug/nes_dmc.c`` at commit ``265ff70``.

    Args:
        note_index: The note the channel reaches, its table step added.

    Returns:
        int: The value the period register holds.
    """
    return BITPHASE_NOISE_PERIOD_COUNT - 1 - note_index % BITPHASE_NOISE_PERIOD_COUNT


def reached_note(
    tuning_table: List[int],
    note_index: int,
    table: LoadedTable,
    tick: int,
) -> int:
    """The note a channel reaches on a tick of a sounding note, held within the tuning table.

    Read from ``processTables`` of ``tracker-pattern-processor.js`` at commit ``265ff70``.

    Args:
        tuning_table: The song's period per note index.
        note_index: The note the pattern cell names.
        table: The table the cell attaches.
        tick: Ticks since the table started.

    Returns:
        int: The note index the channel sounds.
    """
    return min(max(note_index + table.step(tick), 0), len(tuning_table) - 1)


def pattern_volume(carried: int, stored: int) -> int:
    """The level a channel plays at once a row's stored volume cell is read, as the engine reads it.

    A stored ``-1`` silences the channel, a level above zero replaces the one it carries, and any
    other value leaves the carried level alone. A channel opens at the full level. Read from
    ``_processVolume`` of ``tracker-pattern-processor.js`` and ``nes-state.js`` of the tracker at
    commit ``265ff70``. The triangle sounds a full-level instrument while this level is above zero,
    since the driver enables it on the PT3 product of the two, which for a full instrument is the
    pattern level itself.

    Args:
        carried: The level the channel carries into the row.
        stored: The row's stored volume cell.

    Returns:
        int: The level the channel plays the row at.
    """
    if stored == BITPHASE_STORED_VOLUME_OFF:
        return BITPHASE_SILENCED_PATTERN_VOLUME

    if stored > BITPHASE_SILENCED_PATTERN_VOLUME:
        return stored

    return carried


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


def note_value(note: LoadedNote) -> int:
    """The note index a pattern cell names, as ``_processNote`` of the tracker at commit ``265ff70`` reads it."""
    return note.name - BITPHASE_FIRST_NOTE_NAME + (note.octave - BITPHASE_FIRST_OCTAVE) * BITPHASE_NOTE_RANGE


def _next_step(position: int, table: LoadedTable) -> int:
    """The step a table moves to after a tick, circling from its loop where it stands among the steps."""
    following = position + 1
    if following < len(table.rows):
        return following

    return table.loop if 0 < table.loop < len(table.rows) else BITPHASE_FIRST_STEP


def row_speeds(document: LoadedProject) -> List[List[int]]:
    """The ticks each row of every pattern lasts, the order played once through as the engine reads it.

    The song starts at its initial speed, and a speed effect sets the speed from its row on, the last
    one on a row winning across its channels, as ``readLastSpeedCommandOnRow`` of
    ``playback-speed.ts`` reads it. Every speed the export states rides a speed effect's own
    parameter.

    Args:
        document: The document as Bitphase loads it.

    Returns:
        List[List[int]]: One list per pattern of the order, one speed per row.
    """
    song = document.songs[0]
    patterns = {pattern.id: pattern for pattern in song.patterns}
    speed = song.initial_speed
    speeds: List[List[int]] = []
    for pattern_id in document.pattern_order:
        pattern = patterns[pattern_id]
        pattern_speeds: List[int] = []
        for row_index in range(pattern.length):
            for channel in pattern.channels:
                for effect in channel.rows[row_index].effects:
                    if effect is not None and effect.effect == BITPHASE_SPEED_EFFECT and effect.parameter > 0:
                        speed = effect.parameter

            pattern_speeds.append(speed)

        speeds.append(pattern_speeds)

    return speeds


@dataclass
class _ChannelReplay:
    """What one channel carries from row to row while the document plays."""

    note: Optional[int] = None
    table: Optional[LoadedTable] = None
    position: int = BITPHASE_FIRST_STEP

    def read(self, row: LoadedRow, tables: Dict[int, LoadedTable]) -> None:
        """Moves the channel onto one row: its note, then its table, then its effects.

        Read from ``parsePatternRow``, ``_processNote``, ``_processTable`` and
        ``_initChannelOrnamentPosition`` of ``tracker-pattern-processor.js`` at commit ``265ff70``.
        """
        if row.note.name == BITPHASE_NOTE_OFF:
            self.note = None
        elif row.note.name != BITPHASE_NO_NOTE:
            self.note = note_value(row.note)
            self.position = BITPHASE_FIRST_STEP

        if row.table == BITPHASE_TABLE_OFF:
            self.table = None
            self.position = BITPHASE_FIRST_STEP
        elif row.table > 0:
            self.table = tables[row.table - BITPHASE_TABLE_COLUMN_OFFSET]
            self.position = BITPHASE_FIRST_STEP

        for effect in row.effects:
            if effect is not None and effect.effect == BITPHASE_ORNAMENT_POSITION:
                self.position = effect.parameter & BITPHASE_ORNAMENT_POSITION_MASK

    def tick(self, tuning_table: List[int]) -> Optional[int]:
        """The note the channel sounds on one tick, its table stepping on after it.

        Read from ``processTables`` of ``tracker-pattern-processor.js`` at commit ``265ff70``.
        """
        if self.note is None or self.table is None:
            return self.note

        step = self.table.rows[self.position] if self.position < len(self.table.rows) else BITPHASE_FIRST_STEP
        self.position = _next_step(self.position, self.table)
        return min(max(self.note + step, 0), len(tuning_table) - 1)


def played_notes(document: LoadedProject, channel_index: int) -> List[Optional[int]]:
    """The note index one channel sounds on each tick, the order played once through as the engine reads it.

    Args:
        document: The document as Bitphase loads it.
        channel_index: The channel whose notes are read.

    Returns:
        List[Optional[int]]: One note per tick, and ``None`` where the channel holds no note.
    """
    song = document.songs[0]
    patterns = {pattern.id: pattern for pattern in song.patterns}
    tables = {table.id: table for table in document.tables}
    replay = _ChannelReplay()
    notes: List[Optional[int]] = []
    for pattern_id, speeds in zip(document.pattern_order, row_speeds(document)):
        pattern = patterns[pattern_id]
        for row, speed in zip(pattern.channels[channel_index].rows, speeds):
            replay.read(row, tables)
            notes.extend(replay.tick(song.tuning_table) for _ in range(speed))

    return notes
