from __future__ import annotations

from typing import List, Sequence, Tuple

from sampletones_player.specification.screen import (
    HIDDEN_SPRITE_Y,
    SCREEN_COLUMNS,
    SPRITE_ATTRIBUTES_OFFSET,
    SPRITE_BYTES,
    SPRITE_COUNT,
    SPRITE_SCANLINE_DELAY,
    SPRITE_TILE_OFFSET,
    SPRITE_X_OFFSET,
    SPRITE_Y_OFFSET,
    TILE_SIDE,
)
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
from sampletones_tools.player.graphics.deck.meters import meter_members, progress_members
from sampletones_tools.player.graphics.deck.state import (
    MAX_LEVEL,
    DeckState,
    NoiseState,
    PulseState,
    TriangleState,
)
from sampletones_tools.player.graphics.deck.texts import (
    REST_NOTE,
    UNKNOWN_CHARACTER,
    clock_text,
    noise_name,
    pitch_name,
)
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
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet


class Deck:
    """What the player screen shows, stated the way the console holds it.

    The layout says where everything lies and the sheet which tile draws it. Between them every
    rule of the screen is settled here: which tiles a level lights, which shape a duty cycle draws,
    where a pitch stands on the keyboard. The cartridge's own code is held to these answers.
    """

    def __init__(self, layout: ScreenLayout, sheet: TileSheet) -> None:
        self._layout = layout
        self._sheet = sheet

    @classmethod
    def load(cls) -> Deck:
        """The deck the package ships."""
        return cls(ScreenLayout.load(), TileSheet.load())

    def resting(self) -> Picture:
        """The screen before a song is written to it: its fixed elements and labels, every marker hidden."""
        return Picture(
            nametable=self._layout.nametable(self._sheet),
            attributes=self._layout.attribute_table(),
            palette=self._layout.palettes.to_bytes(),
            sprites=self._sprites([]),
        )

    def showing(self, state: DeckState) -> Picture:
        """The screen showing one frame of a song.

        Args:
            state: What the song sounds and where it stands.

        Returns:
            Picture: The resting screen with the song's text, readings and markers written over it.
        """
        cells = bytearray(self._layout.nametable(self._sheet))
        program = self._layout.program
        for field, line in (
            (program.title, state.title),
            (program.artist, state.artist),
            (program.copyright, state.copyright),
        ):
            self._write(cells, field.row, field.column, self._text(self._fitted(line, field.width), TEXT_GROUP))

        transport = self._layout.transport
        self._write(cells, transport.row, transport.state_column, self._tiles(BAR_GROUP, [state.transport.value]))
        self._write(
            cells, transport.row, transport.played_column, self._text(clock_text(state.played_seconds), BAR_GROUP)
        )
        self._write(
            cells, transport.row, transport.total_column, self._text(clock_text(state.total_seconds), BAR_GROUP)
        )

        progress = self._layout.progress
        members = progress_members(state.progress, progress.width)
        self._write(cells, progress.row, progress.column, self._tiles(PROGRESS_GROUP, members))

        channels = self._layout.channels
        self._write_pulse(cells, channels.pulse1_row, state.pulse1)
        self._write_pulse(cells, channels.pulse2_row, state.pulse2)
        self._write_triangle(cells, channels.triangle_row, state.triangle)
        self._write_noise(cells, channels.noise_row, state.noise, shimmer=state.shimmer)

        return Picture(
            nametable=bytes(cells),
            attributes=self._layout.attribute_table(),
            palette=self._layout.palettes.to_bytes(),
            sprites=self._sprites(self._markers(state)),
        )

    def marker_x(self, pitch: int) -> int:
        """The horizontal position of a marker standing over a pitch's key."""
        return self._layout.keyboard.column * TILE_SIDE + pitch * PIXELS_PER_PITCH - PIN_STEM_COLUMN

    def _write_pulse(self, cells: bytearray, row: int, pulse: PulseState) -> None:
        sounding = pulse.level > 0
        wave = PULSE_WAVES[pulse.duty] if sounding else PULSE_REST
        note = pitch_name(pulse.pitch) if sounding else REST_NOTE
        self._write_channel(cells, row, wave, note, self._tiles(PULSE_METER_GROUP, meter_members(pulse.level)))

    def _write_triangle(self, cells: bytearray, row: int, triangle: TriangleState) -> None:
        wave = TRIANGLE_WAVE if triangle.sounding else OTHER_REST
        note = pitch_name(triangle.pitch) if triangle.sounding else REST_NOTE
        level = MAX_LEVEL if triangle.sounding else 0
        self._write_channel(cells, row, wave, note, self._tiles(OTHER_METER_GROUP, meter_members(level)))

    def _write_noise(self, cells: bytearray, row: int, noise: NoiseState, *, shimmer: bool) -> None:
        sounding = noise.level > 0
        wave = NOISE_WAVES[noise.short][int(shimmer)] if sounding else OTHER_REST
        note = noise_name(noise.period) if sounding else REST_NOTE
        self._write_channel(cells, row, wave, note, self._tiles(OTHER_METER_GROUP, meter_members(noise.level)))

    def _write_channel(self, cells: bytearray, row: int, wave: Wave, note: str, meter: Sequence[int]) -> None:
        channels = self._layout.channels
        for offset, names in enumerate((wave.top, wave.bottom)):
            tiles = [self._tile(name) for name in names] * WAVE_PERIODS
            self._write(cells, row + offset, channels.wave_column, tiles)

        self._write(cells, row, channels.note_column, self._text(note, TEXT_GROUP))
        self._write(cells, row, channels.meter_column, meter)

    def _markers(self, state: DeckState) -> List[Tuple[Pin, int, bool]]:
        return [
            (PULSE1_PIN, state.pulse1.pitch, state.pulse1.level > 0),
            (PULSE2_PIN, state.pulse2.pitch, state.pulse2.level > 0),
            (TRIANGLE_PIN, state.triangle.pitch, state.triangle.sounding),
        ]

    def _sprites(self, markers: Sequence[Tuple[Pin, int, bool]]) -> bytes:
        memory = bytearray(SPRITE_COUNT * SPRITE_BYTES)
        for sprite in range(SPRITE_COUNT):
            memory[sprite * SPRITE_BYTES + SPRITE_Y_OFFSET] = HIDDEN_SPRITE_Y

        lane = self._layout.keyboard.lane_row * TILE_SIDE
        for slot, (pin, pitch, sounds) in enumerate(markers):
            if sounds:
                tile = self._sheet.tile(PatternTable.SPRITES, pin.group, pin.member)
                self._place(memory, slot, top=lane, left=self.marker_x(pitch), tile=tile, palette=pin.palette)

        slot = MARKER_SLOTS
        for label in self._layout.labels:
            for offset, character in enumerate(label.text):
                self._place(
                    memory,
                    slot,
                    top=label.row * TILE_SIDE,
                    left=(label.column + offset) * TILE_SIDE,
                    tile=self._sheet.tile(PatternTable.SPRITES, label.group, character),
                    palette=label.palette,
                )
                slot += 1

        return bytes(memory)

    @staticmethod
    def _place(memory: bytearray, slot: int, *, top: int, left: int, tile: int, palette: int) -> None:
        start = slot * SPRITE_BYTES
        memory[start + SPRITE_Y_OFFSET] = top - SPRITE_SCANLINE_DELAY
        memory[start + SPRITE_TILE_OFFSET] = tile
        memory[start + SPRITE_ATTRIBUTES_OFFSET] = palette
        memory[start + SPRITE_X_OFFSET] = left

    def _fitted(self, text: str, width: int) -> str:
        drawn = "".join(character if self._sheet.font.draws(character) else UNKNOWN_CHARACTER for character in text)
        return drawn[:width].ljust(width)

    def _text(self, text: str, group: str) -> List[int]:
        return self._tiles(group, list(text))

    def _tiles(self, group: str, members: Sequence[str]) -> List[int]:
        return [self._sheet.tile(PatternTable.BACKGROUND, group, member) for member in members]

    def _tile(self, name: TileName) -> int:
        return self._sheet.tile(PatternTable.BACKGROUND, name.group, name.member)

    @staticmethod
    def _write(cells: bytearray, row: int, column: int, tiles: Sequence[int]) -> None:
        start = row * SCREEN_COLUMNS + column
        cells[start : start + len(tiles)] = bytes(tiles)
