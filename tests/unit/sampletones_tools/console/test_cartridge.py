from typing import Final, Tuple

from py65.memory import ObservableMemory

from sampletones_player.specification.nsf import PROGRAM_START
from sampletones_tools.console.cartridge import BANK_SIZE, EMPTY_BYTE, FIRST_BANK_REGISTER, Cartridge
from sampletones_tools.console.header import NSFHeader
from tests.unit.sampletones_tools.console.files import NSFFile, bank_offset

BANKS: Final[Tuple[int, ...]] = (0, 2, 0, 0, 0, 0, 0, 0)
MARKS: Final[Tuple[int, ...]] = (0x11, 0x22, 0x33)
SECOND_SLOT: Final[int] = PROGRAM_START + BANK_SIZE


def _banked_file(load: int = PROGRAM_START) -> NSFFile:
    return NSFFile(
        load=load,
        banks=BANKS,
        program={bank_offset(bank): (mark,) for bank, mark in enumerate(MARKS)},
    )


def _cartridge(file: NSFFile) -> Cartridge:
    return Cartridge(NSFHeader.read(file.data), file.image)


class TestBanks:
    def test_a_bank_holds_its_four_kilobytes_of_the_image(self) -> None:
        cartridge = _cartridge(_banked_file())

        assert [cartridge.bank(bank)[0] for bank in range(len(MARKS))] == list(MARKS)
        assert all(len(cartridge.bank(bank)) == BANK_SIZE for bank in range(len(MARKS)))

    def test_a_bank_past_the_image_reads_empty(self) -> None:
        cartridge = _cartridge(_banked_file())

        assert set(cartridge.bank(len(MARKS) + 1)) == {EMPTY_BYTE}

    def test_the_image_is_padded_by_where_the_load_address_falls_in_its_bank(self) -> None:
        offset = 0x0100
        cartridge = _cartridge(_banked_file(load=PROGRAM_START + offset))

        assert cartridge.bank(0)[offset] == MARKS[0]


class TestMounting:
    def test_a_file_loaded_whole_lands_at_its_load_address(self) -> None:
        load = PROGRAM_START + 0x0100
        file = NSFFile(load=load, program={0: (0xAB, 0xCD)})
        memory = ObservableMemory()

        _cartridge(file).mount(memory)

        assert (memory[load], memory[load + 1]) == (0xAB, 0xCD)

    def test_each_slot_starts_with_the_bank_the_header_names(self) -> None:
        memory = ObservableMemory()

        _cartridge(_banked_file()).mount(memory)

        assert (memory[PROGRAM_START], memory[SECOND_SLOT]) == (MARKS[0], MARKS[2])

    def test_a_write_to_a_slots_register_maps_the_bank_written(self) -> None:
        memory = ObservableMemory()
        _cartridge(_banked_file()).mount(memory)

        memory[FIRST_BANK_REGISTER + 1] = 1

        assert memory[SECOND_SLOT] == MARKS[1]
