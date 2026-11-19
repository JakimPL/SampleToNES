from dataclasses import dataclass
from string import printable
from typing import Dict, Final, Sequence, Tuple

from sampletones_player.compression.pitch import PITCH_COUNT
from sampletones_player.specification.program import (
    ARTIST_COLUMNS,
    COPYRIGHT_COLUMNS,
    PROGRESS_PIXELS,
    TITLE_COLUMNS,
)
from sampletones_player.specification.screen import (
    HIDDEN_SPRITE_Y,
    SCREEN_COLUMNS,
    SPRITE_BYTES,
    SPRITE_SCANLINE_DELAY,
    TILE_SIDE,
)
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.deck.groups import (
    BAR_GROUP,
    OTHER_METER_GROUP,
    PROGRESS_GROUP,
    PULSE_METER_GROUP,
    TileName,
)
from sampletones_tools.player.graphics.deck.markers import (
    MARKER_SLOTS,
    PIN_STEM_COLUMN,
    PIXELS_PER_PITCH,
    PULSE1_PIN,
    PULSE2_PIN,
    TRIANGLE_PIN,
    Pin,
)
from sampletones_tools.player.graphics.deck.meters import METER_PAIRS, PROGRESS_STEPS, meter_members
from sampletones_tools.player.graphics.deck.state import NOISE_PERIOD_COUNT, Transport
from sampletones_tools.player.graphics.deck.texts import REST_NOTE, clock_text, noise_name, pitch_name
from sampletones_tools.player.graphics.deck.waves import (
    NOISE_WAVES,
    OTHER_REST,
    PULSE_REST,
    PULSE_WAVES,
    TRIANGLE_WAVE,
    WAVE_PERIODS,
    Wave,
)
from sampletones_tools.player.graphics.layout.screen import TEXT_GROUP, ScreenLayout
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from sampletones_tools.player.graphics.shell.packing import pack

NAMETABLE_START: Final[int] = 0x2000
NOTES_PER_OCTAVE: Final[int] = 12
NOTE_NAME_CELLS: Final[int] = 2
DIGITS: Final[str] = "0123456789"
HEX_DIGITS: Final[str] = DIGITS + "ABCDEF"
CLOCK_CELLS: Final[int] = len(clock_text(0))
CLOCK_COLON: Final[int] = clock_text(0).index(":")
WAVE_ROW_TILES: Final[int] = len(PULSE_REST.top)
PACKED_SCREEN_LIMIT: Final[int] = 0x100
LAST_NOISE_PERIOD: Final[int] = NOISE_PERIOD_COUNT - 1
NOISE_SUFFIX: Final[str] = noise_name(LAST_NOISE_PERIOD)[1:]
METER_CELLS: Final[int] = len(meter_members(0))
WAVE_CELLS: Final[int] = WAVE_PERIODS * len(PULSE_REST.top)
SHOWN_CHARACTERS: Final[str] = "".join(character for character in printable if character.isprintable())
METER_MEMBERS: Final[Tuple[str, ...]] = ("meter_both", "meter_first", "meter_none", "meter_last_lit", "meter_last_dim")
PROGRESS_MEMBERS: Final[Tuple[str, ...]] = tuple(f"progress_{step}" for step in range(PROGRESS_STEPS + 1))


@dataclass(frozen=True)
class ShellData:
    """What the shell is assembled with from the screen layout, the tile sheet and the deck's rules.

    Attributes:
        equates: Named numbers: where each field lies and which tile draws each reading.
        tables: Named runs of bytes: the palette, the packed screen, the labels, the tiles of every
            wave shape and the note names.
    """

    equates: Dict[str, int]
    tables: Dict[str, bytes]


@dataclass(frozen=True)
class WaveTable:
    """Every wave shape the shell draws, laid out in one table it reads by offset.

    The pulse waves open the table, one per duty, so a duty times the size of a wave is its
    offset. Each noise pair overlaps: the shimmering wave starts at the still one's bottom row.

    Attributes:
        tiles: The tiles of every wave, top row then bottom row of each.
        offsets: Where each shape starts in ``tiles``, named as the shell reads it.
    """

    tiles: bytes
    offsets: Dict[str, int]


def shell_data(layout: ScreenLayout, sheet: TileSheet) -> ShellData:
    """States the screen the way the shell draws it.

    The shell draws every reading by a rule simple enough for the console: a note from a name
    table and an octave digit, a meter and the progress bar from neighboring tiles. Each rule is
    held here against the deck it stands for, so the data comes out only where the two agree.

    Raises:
        ValueError: If the sheet or the deck departs from a rule the shell draws by.
    """
    _validate_the_rules(sheet)
    _validate_the_fields(layout, sheet)
    waves = _wave_table(sheet)
    return ShellData(equates={**_equates(layout, sheet), **waves.offsets}, tables=_tables(layout, sheet, waves))


def _cell(row: int, column: int) -> int:
    return NAMETABLE_START + row * SCREEN_COLUMNS + column


def _background(sheet: TileSheet, group: str, member: str) -> int:
    return sheet.tile(PatternTable.BACKGROUND, group, member)


def _tiles(sheet: TileSheet, names: Sequence[TileName]) -> bytes:
    return bytes(_background(sheet, name.group, name.member) for name in names)


def _text(sheet: TileSheet, text: str) -> bytes:
    return bytes(_background(sheet, TEXT_GROUP, character) for character in text)


def _wave(sheet: TileSheet, wave: Wave) -> bytes:
    return _tiles(sheet, wave.top) + _tiles(sheet, wave.bottom)


def _require(holds: bool, rule: str) -> None:
    if not holds:
        raise ValueError(f"the shell draws by a rule the screen departs from: {rule}")


def _consecutive(sheet: TileSheet, group: str, members: Sequence[str]) -> bool:
    first = _background(sheet, group, members[0])
    return [_background(sheet, group, member) for member in members] == list(range(first, first + len(members)))


def _validate_the_rules(sheet: TileSheet) -> None:
    _require(
        all(_background(sheet, TEXT_GROUP, character) == ord(character) for character in SHOWN_CHARACTERS),
        "the text font draws each character at its ASCII code",
    )
    _require(_consecutive(sheet, BAR_GROUP, DIGITS), "the clock's digits stand in order")
    _require(_consecutive(sheet, PROGRESS_GROUP, PROGRESS_MEMBERS), "the progress steps stand in order")
    for group in (PULSE_METER_GROUP, OTHER_METER_GROUP):
        _require(_consecutive(sheet, group, METER_MEMBERS), "a meter's tiles stand in order")

    names = [pitch_name(pitch)[:NOTE_NAME_CELLS] for pitch in range(NOTES_PER_OCTAVE)]
    _require(
        all(
            pitch_name(pitch) == names[pitch % NOTES_PER_OCTAVE] + DIGITS[pitch // NOTES_PER_OCTAVE]
            for pitch in range(PITCH_COUNT)
        ),
        "a note is its name within the octave followed by the octave's digit",
    )
    _require(
        all(
            noise_name(period) == HEX_DIGITS[LAST_NOISE_PERIOD - period] + NOISE_SUFFIX
            for period in range(NOISE_PERIOD_COUNT)
        ),
        "a noise period is named by the hex digit of its distance from the last period, then one suffix",
    )


def _validate_the_fields(layout: ScreenLayout, sheet: TileSheet) -> None:
    program, transport = layout.program, layout.transport
    _require(
        (program.title.width, program.artist.width, program.copyright.width)
        == (TITLE_COLUMNS, ARTIST_COLUMNS, COPYRIGHT_COLUMNS),
        "each line of text takes the columns the program block holds for it",
    )
    _require(
        layout.progress.width * PROGRESS_STEPS == PROGRESS_PIXELS,
        "the progress bar spans the pixels the program block counts",
    )
    colon = layout.nametable(sheet)[transport.row * SCREEN_COLUMNS + transport.total_column + CLOCK_COLON]
    _require(colon == _background(sheet, BAR_GROUP, ":"), "the resting screen shows the total time's colon")


def _wave_table(sheet: TileSheet) -> WaveTable:
    tiles = bytearray()
    offsets: Dict[str, int] = {}
    for name, shapes in (
        ("PULSE_WAVES_OFFSET", PULSE_WAVES),
        ("PULSE_REST_OFFSET", (PULSE_REST,)),
        ("TRIANGLE_WAVE_OFFSET", (TRIANGLE_WAVE,)),
        ("OTHER_REST_OFFSET", (OTHER_REST,)),
    ):
        offsets[name] = len(tiles)
        tiles += b"".join(_wave(sheet, shape) for shape in shapes)

    offsets["NOISE_WAVES_OFFSET"] = len(tiles)
    pairs = [_noise_pair(sheet, *NOISE_WAVES[short]) for short in (False, True)]
    offsets["NOISE_SHIMMER_OFFSET"] = WAVE_ROW_TILES
    offsets["NOISE_SHORT_OFFSET"] = len(pairs[0])
    tiles += b"".join(pairs)
    return WaveTable(tiles=bytes(tiles), offsets=offsets)


def _noise_pair(sheet: TileSheet, still: Wave, shimmering: Wave) -> bytes:
    """A still noise wave and its shimmering one in one run, the second starting at the first's bottom row."""
    still_tiles, shimmering_tiles = _wave(sheet, still), _wave(sheet, shimmering)
    _require(
        shimmering_tiles[:WAVE_ROW_TILES] == still_tiles[WAVE_ROW_TILES:],
        "a shimmering noise wave's top row is the still wave's bottom row",
    )
    return still_tiles + shimmering_tiles[WAVE_ROW_TILES:]


def _pin(sheet: TileSheet, prefix: str, pin: Pin) -> Dict[str, int]:
    return {
        f"{prefix}_PIN_TILE": sheet.tile(PatternTable.SPRITES, pin.group, pin.member),
        f"{prefix}_PIN_PALETTE": pin.palette,
    }


def _meter(sheet: TileSheet, prefix: str, group: str) -> Dict[str, int]:
    return {
        f"{prefix}_METER_NONE": _background(sheet, group, "meter_none"),
        f"{prefix}_METER_LAST_LIT": _background(sheet, group, "meter_last_lit"),
    }


def _channel_cells(layout: ScreenLayout) -> Dict[str, int]:
    channels = layout.channels
    return {
        "PULSE1_CELL": _cell(channels.pulse1_row, channels.wave_column),
        "PULSE2_CELL": _cell(channels.pulse2_row, channels.wave_column),
        "TRIANGLE_CELL": _cell(channels.triangle_row, channels.wave_column),
        "NOISE_CELL": _cell(channels.noise_row, channels.wave_column),
    }


def _equates(layout: ScreenLayout, sheet: TileSheet) -> Dict[str, int]:
    resting = layout.nametable(sheet)
    program, transport, progress = layout.program, layout.transport, layout.progress
    channels, keyboard = layout.channels, layout.keyboard
    channel_cells = channels.meter_column + METER_CELLS - channels.wave_column
    note_offset = channels.note_column - channels.wave_column
    meter_offset = channels.meter_column - channels.wave_column
    written = {
        *range(WAVE_CELLS),
        *range(note_offset, note_offset + len(REST_NOTE)),
        *range(meter_offset, meter_offset + METER_CELLS),
    }
    gaps = {
        resting[row * SCREEN_COLUMNS + channels.wave_column + offset]
        for row in (channels.pulse1_row, channels.pulse2_row, channels.triangle_row, channels.noise_row)
        for offset in range(channel_cells)
        if offset not in written
    }
    _require(len(gaps) == 1, "the cells between a channel's readings show one tile")
    return {
        "NAMETABLE_START": NAMETABLE_START,
        "SCREEN_COLUMNS": SCREEN_COLUMNS,
        "TITLE_CELL": _cell(program.title.row, program.title.column),
        "ARTIST_CELL": _cell(program.artist.row, program.artist.column),
        "COPYRIGHT_CELL": _cell(program.copyright.row, program.copyright.column),
        "TRANSPORT_CELL": _cell(transport.row, transport.state_column),
        "TRANSPORT_CELLS": transport.played_column + CLOCK_CELLS - transport.state_column,
        "PLAYED_OFFSET": transport.played_column - transport.state_column,
        "TOTAL_CELL": _cell(transport.row, transport.total_column),
        "TRANSPORT_GAP_TILE": resting[transport.row * SCREEN_COLUMNS + transport.state_column + 1],
        "COLON_TILE": _background(sheet, BAR_GROUP, ":"),
        "DIGIT_ZERO_TILE": _background(sheet, BAR_GROUP, DIGITS[0]),
        "PLAY_TILE": _background(sheet, BAR_GROUP, Transport.PLAYING.value),
        "PAUSE_TILE": _background(sheet, BAR_GROUP, Transport.PAUSED.value),
        "STOP_TILE": _background(sheet, BAR_GROUP, Transport.STOPPED.value),
        "PROGRESS_CELL": _cell(progress.row, progress.column),
        "PROGRESS_CELLS": progress.width,
        "PROGRESS_STEPS": PROGRESS_STEPS,
        "PROGRESS_EMPTY_TILE": _background(sheet, PROGRESS_GROUP, PROGRESS_MEMBERS[0]),
        **_channel_cells(layout),
        "CHANNEL_CELLS": channel_cells,
        "WAVE_CELLS": WAVE_CELLS,
        "NOTE_OFFSET": note_offset,
        "METER_OFFSET": meter_offset,
        "METER_PAIRS": METER_PAIRS,
        "CHANNEL_GAP_TILE": gaps.pop(),
        "REST_TILE": _background(sheet, TEXT_GROUP, REST_NOTE[0]),
        "OCTAVE_ZERO_TILE": _background(sheet, TEXT_GROUP, DIGITS[0]),
        **_meter(sheet, "PULSE", PULSE_METER_GROUP),
        **_meter(sheet, "OTHER", OTHER_METER_GROUP),
        "HEX_TEN_TILE": _background(sheet, TEXT_GROUP, HEX_DIGITS[len(DIGITS)]),
        "NOISE_SUFFIX_TILE": _background(sheet, TEXT_GROUP, NOISE_SUFFIX[0]),
        "NOISE_SUFFIX_END_TILE": _background(sheet, TEXT_GROUP, NOISE_SUFFIX[1]),
        "LANE_TOP": keyboard.lane_row * TILE_SIDE - SPRITE_SCANLINE_DELAY,
        "KEYBOARD_LEFT": keyboard.column * TILE_SIDE - PIN_STEM_COLUMN,
        "PIXELS_PER_PITCH": PIXELS_PER_PITCH,
        **_pin(sheet, "PULSE1", PULSE1_PIN),
        **_pin(sheet, "PULSE2", PULSE2_PIN),
        **_pin(sheet, "TRIANGLE", TRIANGLE_PIN),
        "MARKER_SLOTS": MARKER_SLOTS,
        "LABEL_SPRITES": sum(len(label.text) for label in layout.labels),
        "HIDDEN_SPRITE_Y": HIDDEN_SPRITE_Y,
        "NOTES_PER_OCTAVE": NOTES_PER_OCTAVE,
    }


def _tables(layout: ScreenLayout, sheet: TileSheet, waves: WaveTable) -> Dict[str, bytes]:
    labels = sum(len(label.text) for label in layout.labels)
    sprites = Deck(layout, sheet).resting().sprites
    screen = pack(layout.nametable(sheet) + layout.attribute_table())
    _require(len(screen) <= PACKED_SCREEN_LIMIT, "the packed screen fits the one-byte index the shell reads it by")
    return {
        "deck_palette": layout.palettes.to_bytes(),
        "deck_screen": screen,
        "deck_labels": sprites[MARKER_SLOTS * SPRITE_BYTES : (MARKER_SLOTS + labels) * SPRITE_BYTES],
        "deck_waves": waves.tiles,
        "note_names": b"".join(_text(sheet, pitch_name(pitch)[:NOTE_NAME_CELLS]) for pitch in range(NOTES_PER_OCTAVE)),
    }
