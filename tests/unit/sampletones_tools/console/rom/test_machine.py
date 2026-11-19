from dataclasses import dataclass
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_player.specification.memory import PROGRAM_START, RAM_SIZE
from sampletones_player.specification.registers import APU_STATUS, PULSE1_CONTROL
from sampletones_tools.console.rom.controller import NO_BUTTONS, Button
from sampletones_tools.console.rom.errors import (
    BootOverrunError,
    ConsoleStateError,
    NotAROMError,
    ReadOnlyMemoryError,
    UnsupportedCartridgeError,
)
from sampletones_tools.console.rom.frame import Frame
from sampletones_tools.console.rom.machine import ROMConsole
from sampletones_tools.console.rom.registers import (
    CONTROL_INTERRUPT_FLAG,
    FIRST_CONTROLLER,
    MASK_BACKGROUND_FLAG,
    NAMETABLES_START,
    PAGE_SIZE,
    SPRITE_TRANSFER,
    VideoRegister,
)
from sampletones_tools.console.rom.timing import (
    DOTS_PER_CYCLE,
    FIRST_VERTICAL_BLANK_DOTS,
    FRAME_CYCLES,
    INTERRUPT_CYCLES,
    SPRITE_TRANSFER_ALIGNMENT_CYCLES,
    SPRITE_TRANSFER_CYCLES,
    VERTICAL_BLANK_CYCLES,
    WARM_UP_CYCLES,
)
from sampletones_tools.player.trace.trace import RegisterTrace
from sampletones_tools.player.trace.write import RegisterWrite
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_tools.console.files import LOAD_ABSOLUTE, absolute
from tests.unit.sampletones_tools.console.rom.files import (
    AND_IMMEDIATE,
    AWAIT_VERTICAL_BLANK,
    INCREMENT_ZERO_PAGE,
    INTERRUPT,
    JUMP_CYCLES,
    LOAD_IMMEDIATE_CYCLES,
    LOAD_ZERO_PAGE,
    NO_OPERATION,
    OUTER_SPIN_CYCLES,
    RESET,
    RETURN_FROM_INTERRUPT,
    RETURN_FROM_INTERRUPT_CYCLES,
    STORE_ABSOLUTE_CYCLES,
    Code,
    ROMFile,
    booting,
    fetch,
    joined,
    load,
    put,
    spin,
    spun_out,
    store,
)

CHANNELS_ON: Final[int] = 0x0F
PLAYED: Final[int] = 0x3F
CLEARED_MEMORY: Final[bytes] = bytes(RAM_SIZE)
COUNTER: Final[int] = 0x10
COUNTER_MIRROR: Final[int] = COUNTER + RAM_SIZE
SEEDED: Final[int] = 0xA5
SPRITE_PAGE: Final[int] = 0x02
TILE: Final[int] = 0x41
BOOT_STRETCHES: Final[int] = 3
LONGEST_INSTRUCTION_CYCLES: Final[int] = 7
FRAMES_COMPARED: Final[int] = 6
BOOT_BUDGET: Final[int] = 200
SPIN_INTO_THE_BLANK: Final[int] = 24
SPIN_PAST_THE_BLANK: Final[int] = 26
BUTTON_READS: Final[int] = 8
OTHER_MAPPER: Final[int] = 4

RETURN: Final[Code] = (RETURN_FROM_INTERRUPT,)
BOOT_SOUND: Final[Code] = put(APU_STATUS, CHANNELS_ON)
PLAY: Final[Code] = joined(put(PULSE1_CONTROL, PLAYED), RETURN)
COUNT: Final[Code] = joined(
    (INCREMENT_ZERO_PAGE, COUNTER),
    (LOAD_ZERO_PAGE, COUNTER),
    store(PULSE1_CONTROL),
    RETURN,
)


def _console(file: ROMFile, memory: bytes = CLEARED_MEMORY) -> ROMConsole:
    return ROMConsole(file.data, memory=memory)


def _booted(file: ROMFile, memory: bytes = CLEARED_MEMORY) -> ROMConsole:
    console = _console(file, memory)
    console.boot()
    return console


def _sounds(console: ROMConsole, frames: int) -> List[Tuple[RegisterWrite, ...]]:
    return [console.frame(NO_BUTTONS).sound for _ in range(frames)]


@pytest.fixture(name="playing")
def playing_fixture() -> ROMFile:
    """A program that enables the channels as it boots and writes one register every frame."""
    return ROMFile.running(booting(setup=BOOT_SOUND), PLAY)


class TestLoading:
    def test_data_without_the_signature_is_refused(self, playing: ROMFile) -> None:
        with pytest.raises(NotAROMError):
            ROMConsole(b"NESM" + playing.data[4:], memory=CLEARED_MEMORY)

    def test_another_board_is_refused(self) -> None:
        with pytest.raises(UnsupportedCartridgeError):
            ROMConsole(ROMFile(mapper=OTHER_MAPPER).data, memory=CLEARED_MEMORY)

    def test_the_memory_given_is_the_consoles_two_kilobytes(self, playing: ROMFile) -> None:
        with pytest.raises(ValueError):
            ROMConsole(playing.data, memory=bytes(RAM_SIZE - 1))


class TestBooting:
    def test_the_boot_comes_back_as_the_stretches_between_its_vertical_blanks(self, playing: ROMFile) -> None:
        frames = _console(playing).boot()

        assert len(frames) == BOOT_STRETCHES

    def test_the_first_vertical_blank_follows_power_on_by_241_scanlines(self, playing: ROMFile) -> None:
        """The flag first rises a dot into scanline 241, which is where a console's first frame reaches it."""
        first = _console(playing).boot()[0]

        reached = FIRST_VERTICAL_BLANK_DOTS // DOTS_PER_CYCLE
        assert reached <= first.cycles <= reached + LONGEST_INSTRUCTION_CYCLES

    def test_what_the_program_writes_before_its_first_interrupt_belongs_to_the_boot(self, playing: ROMFile) -> None:
        frames = _console(playing).boot()

        assert [frame.sound for frame in frames] == [(), (), (RegisterWrite(APU_STATUS, CHANNELS_ON),)]

    def test_the_console_boots_once(self, playing: ROMFile) -> None:
        console = _booted(playing)

        with pytest.raises(ConsoleStateError):
            console.boot()

    def test_a_frame_waits_for_the_boot(self, playing: ROMFile) -> None:
        with pytest.raises(ConsoleStateError):
            _console(playing).frame(NO_BUTTONS)

    def test_a_program_resting_with_its_interrupt_off_is_stopped(self) -> None:
        file = ROMFile.running(spin(RESET), PLAY)

        with pytest.raises(BootOverrunError):
            _console(file).boot()

    def test_a_program_waiting_forever_is_stopped_by_its_step_budget(self) -> None:
        waiting = joined(AWAIT_VERTICAL_BLANK, AWAIT_VERTICAL_BLANK, AWAIT_VERTICAL_BLANK[:3], spin(RESET + 10))
        console = ROMConsole(ROMFile.running(waiting, PLAY).data, memory=CLEARED_MEMORY, step_budget=BOOT_BUDGET)

        with pytest.raises(BootOverrunError):
            console.boot()

    def test_a_store_into_the_program_stops_the_run(self) -> None:
        file = ROMFile.running(booting(setup=put(PROGRAM_START, PLAYED)), PLAY)

        with pytest.raises(ReadOnlyMemoryError):
            _console(file).boot()


class TestFrames:
    def test_the_interrupt_is_delivered_once_a_frame(self) -> None:
        console = _booted(ROMFile.running(booting(), COUNT))

        assert _sounds(console, 3) == [(RegisterWrite(PULSE1_CONTROL, count),) for count in (1, 2, 3)]

    def test_a_frame_answers_with_its_own_writes_alone(self, playing: ROMFile) -> None:
        console = _booted(playing)

        assert _sounds(console, 2) == [(RegisterWrite(PULSE1_CONTROL, PLAYED),)] * 2

    def test_a_trace_holds_the_boot_and_every_frame(self, playing: ROMFile) -> None:
        assert _console(playing).trace(3) == RegisterTrace(
            initialization=(RegisterWrite(APU_STATUS, CHANNELS_ON),),
            play_calls=((RegisterWrite(PULSE1_CONTROL, PLAYED),),) * 3,
        )

    def test_a_frames_work_is_counted_to_where_the_program_comes_to_rest(self, playing: ROMFile) -> None:
        frame = _booted(playing).frame(NO_BUTTONS)

        work = INTERRUPT_CYCLES + LOAD_IMMEDIATE_CYCLES + STORE_ABSOLUTE_CYCLES + RETURN_FROM_INTERRUPT_CYCLES
        assert work <= frame.cycles < work + JUMP_CYCLES

    def test_a_program_still_working_when_the_frame_ends_answers_with_the_whole_frame(self) -> None:
        busy = joined((INCREMENT_ZERO_PAGE, COUNTER), spin(INTERRUPT))
        console = _booted(ROMFile.running(booting(), busy))

        assert console.frame(NO_BUTTONS).cycles >= FRAME_CYCLES


class TestMemory:
    def test_the_program_meets_the_memory_the_console_was_given(self) -> None:
        memory = bytearray(RAM_SIZE)
        memory[COUNTER] = SEEDED
        show = joined(fetch(COUNTER), store(PULSE1_CONTROL), RETURN)
        console = _booted(ROMFile.running(booting(), show), bytes(memory))

        assert console.frame(NO_BUTTONS).sound == (RegisterWrite(PULSE1_CONTROL, SEEDED),)

    def test_the_two_kilobytes_answer_again_through_their_mirrors(self) -> None:
        mirrored = joined(
            put(COUNTER_MIRROR, SEEDED),
            fetch(COUNTER),
            store(PULSE1_CONTROL),
            RETURN,
        )
        console = _booted(ROMFile.running(booting(), mirrored))

        assert console.frame(NO_BUTTONS).sound == (RegisterWrite(PULSE1_CONTROL, SEEDED),)


class TestSound:
    def test_the_sprite_transfer_and_the_controller_stay_out_of_the_sound(self) -> None:
        mixed = joined(
            put(SPRITE_TRANSFER, SPRITE_PAGE),
            put(FIRST_CONTROLLER, 1),
            put(FIRST_CONTROLLER, 0),
            put(PULSE1_CONTROL, PLAYED),
            RETURN,
        )
        frame = _booted(ROMFile.running(booting(), mixed)).frame(NO_BUTTONS)

        assert frame.sound == (RegisterWrite(PULSE1_CONTROL, PLAYED),)
        assert [write.address for write in frame.video] == [SPRITE_TRANSFER]


class TestVideoWrites:
    def test_a_store_is_stamped_with_the_cycle_it_completes_on(self) -> None:
        stores = joined(put(VideoRegister.MASK.address, 0), store(VideoRegister.SCROLL.address), RETURN)
        frame = _booted(ROMFile.running(booting(), stores)).frame(NO_BUTTONS)

        first, second = (write.cycle for write in frame.video)
        landed = INTERRUPT_CYCLES + LOAD_IMMEDIATE_CYCLES + STORE_ABSOLUTE_CYCLES
        assert landed <= first < landed + JUMP_CYCLES
        assert second - first == STORE_ABSOLUTE_CYCLES

    def test_a_store_states_whether_the_picture_was_being_drawn(self) -> None:
        drawing = joined(
            put(VideoRegister.MASK.address, MASK_BACKGROUND_FLAG),
            store(VideoRegister.SCROLL.address),
            RETURN,
        )
        console = _booted(ROMFile.running(booting(), drawing))

        frames = [console.frame(NO_BUTTONS) for _ in range(2)]

        assert [[write.rendering for write in frame.video] for frame in frames] == [[False, True], [True, True]]

    def test_a_store_inside_the_warm_up_says_so_and_changes_nothing(self) -> None:
        """The processor ignores its control register for about 29658 cycles after power-on."""
        early = put(VideoRegister.CONTROL.address, CONTROL_INTERRUPT_FLAG)
        frames = _console(ROMFile.running(booting(before=early), PLAY)).boot()

        stores = [write for frame in frames for write in frame.video]
        assert [(write.value, write.warming) for write in stores] == [
            (CONTROL_INTERRUPT_FLAG, True),
            (CONTROL_INTERRUPT_FLAG, False),
        ]
        assert len(frames) == BOOT_STRETCHES
        assert WARM_UP_CYCLES == 29658

    def test_a_sprite_transfer_fills_the_sprite_memory_and_holds_the_processor(self) -> None:
        """A transfer stalls the CPU for 513 cycles, and for one more where it begins on an odd cycle."""
        memory = bytearray(RAM_SIZE)
        page = bytes(index % 251 for index in range(PAGE_SIZE))
        memory[SPRITE_PAGE * PAGE_SIZE : (SPRITE_PAGE + 1) * PAGE_SIZE] = page
        transfer = joined(put(SPRITE_TRANSFER, SPRITE_PAGE), store(VideoRegister.SPRITE_ADDRESS.address), RETURN)
        console = _booted(ROMFile.running(booting(), transfer), bytes(memory))

        frame = console.frame(NO_BUTTONS)

        first, second = (write.cycle for write in frame.video)
        stalled = second - first - STORE_ABSOLUTE_CYCLES
        assert console.screen.sprites == page
        assert SPRITE_TRANSFER_CYCLES == 513
        assert stalled in (SPRITE_TRANSFER_CYCLES, SPRITE_TRANSFER_CYCLES + SPRITE_TRANSFER_ALIGNMENT_CYCLES)

    def test_a_tile_stored_while_booting_shows_on_the_screen(self) -> None:
        tile = joined(
            put(VideoRegister.ADDRESS.address, NAMETABLES_START >> 8),
            put(VideoRegister.ADDRESS.address, NAMETABLES_START & 0xFF),
            put(VideoRegister.DATA.address, TILE),
            put(VideoRegister.SCROLL.address, 0),
            store(VideoRegister.SCROLL.address),
        )
        console = _booted(ROMFile.running(booting(setup=tile), PLAY))

        screen = console.screen
        assert (screen.nametable[0], screen.scroll_x, screen.scroll_y) == (TILE, 0, 0)


class TestTheLateInterrupt:
    """Asking for interrupts while the vertical blank flag still stands delivers one at once, as the hardware does."""

    def test_an_interrupt_asked_for_inside_the_blank_arrives_before_the_next_frame(self) -> None:
        file = ROMFile.running(booting(setup=spun_out(SPIN_INTO_THE_BLANK)), PLAY)

        frames = _console(file).boot()

        assert SPIN_INTO_THE_BLANK * OUTER_SPIN_CYCLES - FRAME_CYCLES in range(VERTICAL_BLANK_CYCLES)
        assert frames[-1].sound == (RegisterWrite(PULSE1_CONTROL, PLAYED),)

    def test_an_interrupt_asked_for_past_the_blank_waits_for_the_next_frame(self) -> None:
        file = ROMFile.running(booting(setup=spun_out(SPIN_PAST_THE_BLANK)), PLAY)

        frames = _console(file).boot()

        assert SPIN_PAST_THE_BLANK * OUTER_SPIN_CYCLES - FRAME_CYCLES > VERTICAL_BLANK_CYCLES
        assert frames[-1].sound == ()


class TestTheController:
    def test_the_buttons_held_through_a_frame_reach_the_programs_reads(self) -> None:
        read = joined(
            (LOAD_ABSOLUTE, *absolute(FIRST_CONTROLLER)),
            (AND_IMMEDIATE, 1),
            store(PULSE1_CONTROL),
        )
        reading = joined(put(FIRST_CONTROLLER, 1), put(FIRST_CONTROLLER, 0), read * BUTTON_READS, RETURN)
        console = _booted(ROMFile.running(booting(), reading))

        frame = console.frame(Button.A | Button.START)

        assert [write.value for write in frame.sound] == [1, 0, 0, 1, 0, 0, 0, 0]


class TestWatchedAddresses:
    def test_a_frame_records_when_the_program_reaches_a_watched_address(self, playing: ROMFile) -> None:
        console = ROMConsole(playing.data, memory=CLEARED_MEMORY, watched=frozenset({INTERRUPT}))
        console.boot()

        frames = [console.frame(NO_BUTTONS) for _ in range(2)]

        for frame in frames:
            (arrival,) = frame.arrivals
            assert arrival.address == INTERRUPT
            assert INTERRUPT_CYCLES <= arrival.cycle < INTERRUPT_CYCLES + JUMP_CYCLES

    def test_a_loop_passing_a_watched_address_is_stepped_in_full(self, playing: ROMFile) -> None:
        rest = RESET + len(booting(setup=BOOT_SOUND)) - len(spin(RESET))
        console = ROMConsole(playing.data, memory=CLEARED_MEMORY, watched=frozenset({rest}))
        console.boot()

        frame = console.frame(NO_BUTTONS)

        assert frame.cycles >= FRAME_CYCLES
        assert len(frame.arrivals) > FRAME_CYCLES // (2 * JUMP_CYCLES)
        assert {arrival.address for arrival in frame.arrivals} == {rest}


class TestSkippingIdleLoops(BaseTestSuite):
    """Moving the clock over the turns of an idle loop plays the frames stepping every turn plays."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        rest: Callable[[int], Code]

    test_cases: Tuple[TestCase, ...] = (
        TestCase(label="a-jump-to-itself", rest=spin),
        TestCase(
            label="a-loop-reading-memory",
            rest=lambda address: joined((LOAD_ZERO_PAGE, COUNTER), spin(address)),
        ),
        TestCase(
            label="a-longer-loop",
            rest=lambda address: joined((NO_OPERATION, NO_OPERATION, NO_OPERATION), spin(address)),
        ),
    )

    @staticmethod
    def _frames(file: ROMFile, *, skip_idle_loops: bool) -> List[Frame]:
        console = ROMConsole(file.data, memory=CLEARED_MEMORY, skip_idle_loops=skip_idle_loops)
        frames = list(console.boot())
        frames.extend(console.frame(NO_BUTTONS) for _ in range(FRAMES_COMPARED))
        return frames

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_both_ways_play_the_same_frames(self, test_case: TestCase) -> None:
        working = joined(
            put(SPRITE_TRANSFER, SPRITE_PAGE),
            put(VideoRegister.MASK.address, MASK_BACKGROUND_FLAG),
            (INCREMENT_ZERO_PAGE, COUNTER),
            (LOAD_ZERO_PAGE, COUNTER),
            store(PULSE1_CONTROL),
            RETURN,
        )
        file = ROMFile.running(booting(setup=BOOT_SOUND, rest=test_case.rest), working)

        skipped = self._frames(file, skip_idle_loops=True)
        stepped = self._frames(file, skip_idle_loops=False)

        assert skipped == stepped
