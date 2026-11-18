from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_player.specification.rom import PATTERN_UNIT_SIZE
from sampletones_tools.console.rom.errors import ReadOnlyMemoryError
from sampletones_tools.console.rom.header import Mirroring
from sampletones_tools.console.rom.registers import (
    COLOR_MASK,
    COLUMN_STEP,
    CONTROL_COLUMN_STEP_FLAG,
    CONTROL_INTERRUPT_FLAG,
    MASK_BACKGROUND_FLAG,
    MASK_SPRITES_FLAG,
    NAMETABLE_SIZE,
    NAMETABLE_TILES,
    NAMETABLES_START,
    PAGE_SIZE,
    PALETTE_SIZE,
    PALETTE_START,
    SPRITE_MEMORY_SIZE,
    STATUS_VERTICAL_BLANK_FLAG,
    VideoRegister,
)
from sampletones_tools.console.rom.video import Video
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PATTERNS: Final[bytes] = bytes(index % 251 for index in range(PATTERN_UNIT_SIZE))
FIRST_TABLE: Final[int] = NAMETABLES_START
SECOND_TABLE: Final[int] = FIRST_TABLE + NAMETABLE_SIZE
THIRD_TABLE: Final[int] = SECOND_TABLE + NAMETABLE_SIZE
FOURTH_TABLE: Final[int] = THIRD_TABLE + NAMETABLE_SIZE
NAMETABLES_MIRROR: Final[int] = 0x3000
PALETTE_MIRROR: Final[int] = PALETTE_START + PALETTE_SIZE
SPRITE_BACKDROP: Final[int] = PALETTE_START + 0x10
SPRITE_COLOR: Final[int] = PALETTE_START + 0x11
PATTERN_ADDRESS: Final[int] = 0x0123
MARK: Final[int] = 0x5A
OTHER_MARK: Final[int] = 0xA5
TILES: Final[Tuple[int, ...]] = (0x41, 0x42, 0x43)
SECOND_NAMETABLE: Final[int] = 0x01
ADDRESS_HIGH_SHIFT: Final[int] = 8
BYTE_MASK: Final[int] = 0xFF
ORIGIN: Final[Tuple[int, int]] = (0, 0)


def _warmed(mirroring: Mirroring) -> Video:
    video = Video(PATTERNS, mirroring)
    video.finish_warming()
    return video


def _point(video: Video, address: int) -> None:
    video.write(VideoRegister.ADDRESS, address >> ADDRESS_HIGH_SHIFT)
    video.write(VideoRegister.ADDRESS, address & BYTE_MASK)


def _store(video: Video, address: int, *values: int) -> None:
    _point(video, address)
    for value in values:
        video.write(VideoRegister.DATA, value)


def _load(video: Video, address: int) -> int:
    """Reads one byte the way a program does: the first read fills the buffer the second answers from."""
    _point(video, address)
    video.read(VideoRegister.DATA)
    _point(video, address)
    return video.read(VideoRegister.DATA)


@pytest.fixture(name="video")
def video_fixture() -> Video:
    """A picture processor past its warm-up, over a board folding its nametables horizontally."""
    return _warmed(Mirroring.HORIZONTAL)


class TestWarmUp(BaseTestSuite):
    """For a stretch after power-on the processor ignores four of its registers and takes the rest."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        register: VideoRegister
        value: int
        expected: bool

    test_cases: Tuple[TestCase, ...] = (
        TestCase(label="control", register=VideoRegister.CONTROL, value=CONTROL_INTERRUPT_FLAG, expected=False),
        TestCase(label="mask", register=VideoRegister.MASK, value=MASK_BACKGROUND_FLAG, expected=False),
        TestCase(label="scroll", register=VideoRegister.SCROLL, value=MARK, expected=False),
        TestCase(label="address", register=VideoRegister.ADDRESS, value=0x20, expected=False),
        TestCase(label="sprite-data", register=VideoRegister.SPRITE_DATA, value=MARK, expected=True),
    )

    @staticmethod
    def _state(video: Video) -> Tuple[int, int, int, int, bytes]:
        screen = video.screen
        return screen.control, screen.mask, screen.scroll_x, screen.scroll_y, screen.sprites

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_store_inside_the_warm_up_is_taken_or_ignored(self, test_case: TestCase) -> None:
        video = Video(PATTERNS, Mirroring.HORIZONTAL)
        untouched = self._state(video)

        video.write(test_case.register, test_case.value)
        video.write(test_case.register, test_case.value)

        assert (self._state(video) != untouched) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_store_is_taken_once_the_warm_up_ends(self, test_case: TestCase) -> None:
        video = _warmed(Mirroring.HORIZONTAL)
        untouched = self._state(video)

        video.write(test_case.register, test_case.value)
        video.write(test_case.register, test_case.value)

        assert self._state(video) != untouched

    def test_the_processor_reports_its_warm_up_until_told_it_ended(self) -> None:
        video = Video(PATTERNS, Mirroring.HORIZONTAL)
        warming = video.warming
        video.finish_warming()

        assert (warming, video.warming) == (True, False)


class TestAddressing:
    def test_two_stores_to_the_address_register_say_where_data_lands(self, video: Video) -> None:
        _store(video, FIRST_TABLE, *TILES)

        assert video.screen.nametable[: len(TILES)] == bytes(TILES)

    def test_data_steps_down_a_column_where_the_control_register_asks(self, video: Video) -> None:
        video.write(VideoRegister.CONTROL, CONTROL_COLUMN_STEP_FLAG)
        _store(video, FIRST_TABLE, *TILES)
        video.write(VideoRegister.CONTROL, 0)

        nametable = video.screen.nametable
        assert [nametable[row * COLUMN_STEP] for row in range(len(TILES))] == list(TILES)

    def test_a_status_read_resets_the_latch_the_two_stores_share(self, video: Video) -> None:
        video.write(VideoRegister.ADDRESS, PALETTE_START >> ADDRESS_HIGH_SHIFT)
        video.read(VideoRegister.STATUS)
        _store(video, FIRST_TABLE, MARK)

        assert video.screen.nametable[0] == MARK

    def test_a_store_into_the_pattern_tables_is_refused(self, video: Video) -> None:
        with pytest.raises(ReadOnlyMemoryError):
            _store(video, PATTERN_ADDRESS, MARK)


class TestReading:
    def test_a_data_read_answers_with_what_the_read_before_it_fetched(self, video: Video) -> None:
        _store(video, FIRST_TABLE, *TILES)
        _point(video, FIRST_TABLE)

        reads: List[int] = [video.read(VideoRegister.DATA) for _ in range(len(TILES) + 1)]

        assert reads[1:] == list(TILES)

    def test_the_palette_answers_at_once(self, video: Video) -> None:
        _store(video, SPRITE_COLOR, MARK & COLOR_MASK)
        _point(video, SPRITE_COLOR)

        assert video.read(VideoRegister.DATA) == MARK & COLOR_MASK

    def test_the_pattern_tables_read_as_the_cartridge_holds_them(self, video: Video) -> None:
        assert _load(video, PATTERN_ADDRESS) == PATTERNS[PATTERN_ADDRESS]

    def test_a_register_that_only_takes_stores_reads_as_zero(self, video: Video) -> None:
        video.write(VideoRegister.MASK, MASK_SPRITES_FLAG)

        assert video.read(VideoRegister.MASK) == 0


class TestNametableFolding(BaseTestSuite):
    """A board holds two nametables and answers at four, and its mirroring says which share their bytes."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        mirroring: Mirroring
        written: int
        expected: Tuple[int, ...]

    test_cases: Tuple[TestCase, ...] = (
        TestCase(
            label="horizontal-first",
            mirroring=Mirroring.HORIZONTAL,
            written=FIRST_TABLE,
            expected=(FIRST_TABLE, SECOND_TABLE, NAMETABLES_MIRROR),
        ),
        TestCase(
            label="horizontal-third",
            mirroring=Mirroring.HORIZONTAL,
            written=THIRD_TABLE,
            expected=(THIRD_TABLE, FOURTH_TABLE),
        ),
        TestCase(
            label="vertical-first",
            mirroring=Mirroring.VERTICAL,
            written=FIRST_TABLE,
            expected=(FIRST_TABLE, THIRD_TABLE, NAMETABLES_MIRROR),
        ),
        TestCase(
            label="vertical-second",
            mirroring=Mirroring.VERTICAL,
            written=SECOND_TABLE,
            expected=(SECOND_TABLE, FOURTH_TABLE),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_byte_shows_at_every_address_sharing_it_and_at_no_other(self, test_case: TestCase) -> None:
        video = _warmed(test_case.mirroring)
        _store(video, test_case.written, MARK)

        shown = tuple(
            address
            for address in (FIRST_TABLE, SECOND_TABLE, THIRD_TABLE, FOURTH_TABLE, NAMETABLES_MIRROR)
            if _load(video, address) == MARK
        )

        assert shown == test_case.expected


class TestThePalette:
    def test_a_sprite_palettes_first_entry_is_the_backgrounds_own(self, video: Video) -> None:
        _store(video, SPRITE_BACKDROP, MARK & COLOR_MASK)

        palette = video.screen.palette
        assert (palette[0], palette[SPRITE_BACKDROP - PALETTE_START]) == (MARK & COLOR_MASK,) * 2

    def test_the_palette_repeats_through_the_rest_of_its_page(self, video: Video) -> None:
        _store(video, PALETTE_MIRROR + 1, MARK & COLOR_MASK)

        assert video.screen.palette[1] == MARK & COLOR_MASK

    def test_an_entry_keeps_the_six_bits_a_color_takes(self, video: Video) -> None:
        _store(video, SPRITE_COLOR, BYTE_MASK)

        assert video.screen.palette[SPRITE_COLOR - PALETTE_START] == COLOR_MASK


class TestVerticalBlank:
    def test_a_frame_beginning_sets_the_flag_a_status_read_clears(self, video: Video) -> None:
        video.begin_vertical_blank()

        reads = (video.read(VideoRegister.STATUS), video.read(VideoRegister.STATUS))

        assert reads == (STATUS_VERTICAL_BLANK_FLAG, 0)

    def test_the_blank_ending_clears_the_flag(self, video: Video) -> None:
        video.begin_vertical_blank()
        video.end_vertical_blank()

        assert not video.vertical_blank

    def test_an_interrupt_is_due_where_the_control_register_asks_for_one(self, video: Video) -> None:
        video.begin_vertical_blank()
        unasked = video.take_interrupt()
        video.read(VideoRegister.STATUS)
        video.write(VideoRegister.CONTROL, CONTROL_INTERRUPT_FLAG)
        video.begin_vertical_blank()

        assert (unasked, video.take_interrupt()) == (False, True)

    def test_an_interrupt_taken_is_delivered_once(self, video: Video) -> None:
        video.write(VideoRegister.CONTROL, CONTROL_INTERRUPT_FLAG)
        video.begin_vertical_blank()
        video.take_interrupt()

        assert not video.take_interrupt()

    def test_asking_for_interrupts_while_the_flag_stands_raises_one_at_once(self, video: Video) -> None:
        video.begin_vertical_blank()
        video.write(VideoRegister.CONTROL, CONTROL_INTERRUPT_FLAG)

        assert video.take_interrupt()

    def test_asking_once_the_flag_was_read_waits_for_the_next_frame(self, video: Video) -> None:
        video.begin_vertical_blank()
        video.read(VideoRegister.STATUS)
        video.write(VideoRegister.CONTROL, CONTROL_INTERRUPT_FLAG)

        assert not video.take_interrupt()


class TestSprites:
    def test_sprite_data_lands_at_the_sprite_address_and_steps_it(self, video: Video) -> None:
        video.write(VideoRegister.SPRITE_ADDRESS, 4)
        video.write(VideoRegister.SPRITE_DATA, MARK)
        video.write(VideoRegister.SPRITE_DATA, OTHER_MARK)

        assert video.screen.sprites[4:6] == bytes((MARK, OTHER_MARK))

    def test_sprite_data_reads_back_where_the_address_stands(self, video: Video) -> None:
        video.write(VideoRegister.SPRITE_ADDRESS, 4)
        video.write(VideoRegister.SPRITE_DATA, MARK)
        video.write(VideoRegister.SPRITE_ADDRESS, 4)

        assert video.read(VideoRegister.SPRITE_DATA) == MARK

    def test_a_transfer_copies_a_page_from_the_sprite_address_round(self, video: Video) -> None:
        page = [index % PAGE_SIZE for index in range(PAGE_SIZE)]
        video.write(VideoRegister.SPRITE_ADDRESS, 2)

        video.transfer(page)

        sprites = video.screen.sprites
        assert (sprites[2], sprites[SPRITE_MEMORY_SIZE - 1], sprites[0], sprites[1]) == (
            page[0],
            page[SPRITE_MEMORY_SIZE - 3],
            page[SPRITE_MEMORY_SIZE - 2],
            page[SPRITE_MEMORY_SIZE - 1],
        )


class TestTheScreen:
    def test_the_screen_shows_the_nametable_the_control_register_selects(self, video: Video) -> None:
        _store(video, THIRD_TABLE, *TILES)
        video.write(VideoRegister.CONTROL, SECOND_NAMETABLE << 1)

        assert video.screen.nametable[: len(TILES)] == bytes(TILES)

    def test_the_attributes_are_the_bytes_behind_the_tiles(self, video: Video) -> None:
        _store(video, FIRST_TABLE + NAMETABLE_TILES, MARK)
        video.write(VideoRegister.CONTROL, 0)

        assert video.screen.attributes[0] == MARK

    def test_the_screen_states_the_mask_and_the_control_register(self, video: Video) -> None:
        video.write(VideoRegister.CONTROL, CONTROL_INTERRUPT_FLAG)
        video.write(VideoRegister.MASK, MASK_BACKGROUND_FLAG | MASK_SPRITES_FLAG)

        screen = video.screen
        assert (screen.control, screen.mask, video.rendering, video.interrupts) == (
            CONTROL_INTERRUPT_FLAG,
            MASK_BACKGROUND_FLAG | MASK_SPRITES_FLAG,
            True,
            True,
        )

    def test_two_stores_to_the_scroll_register_place_the_picture(self, video: Video) -> None:
        video.write(VideoRegister.SCROLL, 13)
        video.write(VideoRegister.SCROLL, 77)

        screen = video.screen
        assert (screen.scroll_x, screen.scroll_y) == (13, 77)

    def test_an_address_left_standing_displaces_the_picture_until_the_scroll_is_restored(self, video: Video) -> None:
        """The address and scroll registers share their bits, so a program restores the scroll behind its last store."""
        _store(video, SECOND_TABLE + COLUMN_STEP, MARK)
        displaced = video.screen
        video.write(VideoRegister.CONTROL, 0)
        video.write(VideoRegister.SCROLL, 0)
        video.write(VideoRegister.SCROLL, 0)
        restored = video.screen

        assert (displaced.scroll_x, displaced.scroll_y) != ORIGIN
        assert (restored.scroll_x, restored.scroll_y) == ORIGIN
