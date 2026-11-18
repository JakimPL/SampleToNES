from typing import Final

import pytest

from sampletones_player.compression.pitch import PITCH_COUNT
from sampletones_player.specification.screen import SPRITE_BYTES
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.deck.markers import MARKER_SLOTS
from sampletones_tools.player.graphics.deck.state import DUTY_COUNT, NOISE_PERIOD_COUNT
from sampletones_tools.player.graphics.deck.texts import noise_name, pitch_name
from sampletones_tools.player.graphics.deck.waves import NOISE_WAVES, PULSE_WAVES, TRIANGLE_WAVE, Wave
from sampletones_tools.player.graphics.layout.screen import TEXT_GROUP, ScreenLayout
from sampletones_tools.player.graphics.sheet.groups import PatternTable, SheetGroups
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from sampletones_tools.player.graphics.shell.data import NOTE_NAME_CELLS, NOTES_PER_OCTAVE, ShellData, shell_data
from sampletones_tools.player.graphics.shell.packing import unpack
from tests.suite.base import BaseTestSuite

WAVE_TABLE_SIZE: Final[int] = 4
NAME_CELLS: Final[int] = 3


@pytest.fixture(name="data", scope="module")
def data_fixture() -> ShellData:
    return shell_data(ScreenLayout.load(), TileSheet.load())


def text_tiles(sheet: TileSheet, text: str) -> bytes:
    return bytes(sheet.tile(PatternTable.BACKGROUND, TEXT_GROUP, character) for character in text)


def wave_tiles(sheet: TileSheet, wave: Wave) -> bytes:
    names = (*wave.top, *wave.bottom)
    return bytes(sheet.tile(PatternTable.BACKGROUND, name.group, name.member) for name in names)


def regrouped(sheet: TileSheet, group: str, first: int) -> TileSheet:
    """The sheet with one background group moved to start at another tile."""
    groups = tuple(
        tile_group.model_copy(update={"first": first}) if tile_group.name == group else tile_group
        for tile_group in sheet.groups.background
    )
    return sheet.model_copy(update={"groups": SheetGroups(background=groups, sprites=sheet.groups.sprites)})


class TestTheShellData(BaseTestSuite):
    """The shell draws the deck from these tables, so each is held against the deck's own rules."""

    def test_the_packed_screen_unpacks_into_the_resting_screen(
        self, data: ShellData, shipped_layout: ScreenLayout, shipped_sheet: TileSheet
    ) -> None:
        expected = shipped_layout.nametable(shipped_sheet) + shipped_layout.attribute_table()

        assert unpack(data.tables["deck_screen"]) == expected

    def test_the_labels_are_the_sprites_the_deck_rests_with(self, data: ShellData, shipped_deck: Deck) -> None:
        labels = data.tables["deck_labels"]
        start = MARKER_SLOTS * SPRITE_BYTES

        assert labels == shipped_deck.resting().sprites[start : start + len(labels)]

    def test_the_palette_is_the_layout_s(self, data: ShellData, shipped_layout: ScreenLayout) -> None:
        assert data.tables["deck_palette"] == shipped_layout.palettes.to_bytes()

    def test_every_pitch_is_named_by_its_note_and_its_octave(self, data: ShellData, shipped_sheet: TileSheet) -> None:
        names = data.tables["note_names"]
        zero = data.equates["OCTAVE_ZERO_TILE"]

        for pitch in range(PITCH_COUNT):
            note = (pitch % NOTES_PER_OCTAVE) * NOTE_NAME_CELLS
            shown = names[note : note + NOTE_NAME_CELLS] + bytes([zero + pitch // NOTES_PER_OCTAVE])
            assert shown == text_tiles(shipped_sheet, pitch_name(pitch))

    def test_every_noise_period_is_named(self, data: ShellData, shipped_sheet: TileSheet) -> None:
        names = data.tables["noise_names"]

        for period in range(NOISE_PERIOD_COUNT):
            shown = names[period * NAME_CELLS : (period + 1) * NAME_CELLS]
            assert shown == text_tiles(shipped_sheet, noise_name(period))

    def test_every_duty_draws_the_deck_s_wave(self, data: ShellData, shipped_sheet: TileSheet) -> None:
        waves = data.tables["pulse_waves"]

        for duty in range(DUTY_COUNT):
            shown = waves[duty * WAVE_TABLE_SIZE : (duty + 1) * WAVE_TABLE_SIZE]
            assert shown == wave_tiles(shipped_sheet, PULSE_WAVES[duty])

    def test_the_noise_waves_follow_the_sequence_then_the_shimmer(
        self, data: ShellData, shipped_sheet: TileSheet
    ) -> None:
        waves = data.tables["noise_waves"]
        expected = b"".join(wave_tiles(shipped_sheet, wave) for short in (False, True) for wave in NOISE_WAVES[short])

        assert waves == expected

    def test_the_triangle_draws_the_deck_s_wave(self, data: ShellData, shipped_sheet: TileSheet) -> None:
        assert data.tables["triangle_wave"] == wave_tiles(shipped_sheet, TRIANGLE_WAVE)


class TestASheetTheShellCannotDraw(BaseTestSuite):
    def test_a_font_away_from_the_ascii_codes_is_refused(
        self, shipped_layout: ScreenLayout, shipped_sheet: TileSheet
    ) -> None:
        moved = regrouped(shipped_sheet, TEXT_GROUP, shipped_sheet.table(PatternTable.BACKGROUND)[TEXT_GROUP].first + 1)

        with pytest.raises(ValueError, match="ASCII"):
            shell_data(shipped_layout, moved)

    def test_a_title_field_of_another_width_is_refused(
        self, shipped_layout: ScreenLayout, shipped_sheet: TileSheet
    ) -> None:
        program = shipped_layout.program
        title = program.title.model_copy(update={"width": program.title.width - 1})
        narrowed = shipped_layout.model_copy(update={"program": program.model_copy(update={"title": title})})

        with pytest.raises(ValueError, match="columns the program block holds"):
            shell_data(narrowed, shipped_sheet)
