from typing import Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.shell.image import ShellImage
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.program import PROGRAM_BLOCK_SIZE, UNWRITTEN_BYTE
from sampletones_player.specification.shell import ADDRESS_SPACE_END, VECTORS_SIZE
from tests.suite.base import BaseTestSuite

SONG_ADDRESS: Final[int] = 0x8316
RETURN_FROM_INTERRUPT: Final[int] = 0x40
CODE_SIZE: Final[int] = 4
SHELL_SIZE: Final[int] = PROGRAM_BLOCK_SIZE + CODE_SIZE + VECTORS_SIZE
START: Final[int] = ADDRESS_SPACE_END - SHELL_SIZE
FIRST_ROUTINE: Final[int] = START + PROGRAM_BLOCK_SIZE
FRAME: Final[int] = FIRST_ROUTINE + 1
POWER_ON: Final[int] = FIRST_ROUTINE + 2
INTERRUPT: Final[int] = FIRST_ROUTINE + 3
BYTE_ORDER: Final = "little"


def word(value: int) -> bytes:
    return value.to_bytes(WORD_SIZE, BYTE_ORDER)


def shell_code(vectors: Tuple[int, int, int]) -> bytes:
    """A shell of an unwritten block naming the song, four bytes of code and three vectors."""
    block = word(SONG_ADDRESS) + bytes([UNWRITTEN_BYTE]) * (PROGRAM_BLOCK_SIZE - WORD_SIZE)
    code = bytes([RETURN_FROM_INTERRUPT]) * CODE_SIZE
    return block + code + b"".join(word(vector) for vector in vectors)


SHELL: Final[ShellImage] = ShellImage(code=shell_code((FRAME, POWER_ON, INTERRUPT)))


class TestAShellImage(BaseTestSuite):
    def test_it_ends_at_the_top_of_the_address_space(self) -> None:
        assert SHELL.start + len(SHELL.code) == ADDRESS_SPACE_END

    def test_it_reads_the_song_address_it_was_built_with(self) -> None:
        assert SHELL.linked_song == SONG_ADDRESS

    def test_it_reads_its_vectors_in_the_console_order(self) -> None:
        assert SHELL.vectors == (FRAME, POWER_ON, INTERRUPT)

    def test_the_shipped_shell_reads_back(self) -> None:
        shipped = ShellImage.load()

        assert shipped.start + len(shipped.code) == ADDRESS_SPACE_END


class TestAShellImageTheModelRefuses(BaseTestSuite):
    def test_a_vector_into_the_program_block_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="outside the shell's code"):
            ShellImage(code=shell_code((START, POWER_ON, INTERRUPT)))

    def test_a_vector_into_the_vectors_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="outside the shell's code"):
            ShellImage(code=shell_code((FRAME, ADDRESS_SPACE_END - WORD_SIZE, INTERRUPT)))

    def test_a_shell_shorter_than_its_block_and_vectors_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="code"):
            ShellImage(code=bytes(PROGRAM_BLOCK_SIZE))


class TestTheProgramBlockWritten(BaseTestSuite):
    @staticmethod
    def block(song: int) -> bytes:
        return word(song) + bytes(range(PROGRAM_BLOCK_SIZE - WORD_SIZE))

    def test_the_block_replaces_the_first_bytes_and_nothing_else(self) -> None:
        written = SHELL.with_program(self.block(SONG_ADDRESS))

        assert written[:PROGRAM_BLOCK_SIZE] == self.block(SONG_ADDRESS)
        assert written[PROGRAM_BLOCK_SIZE:] == SHELL.code[PROGRAM_BLOCK_SIZE:]

    def test_a_block_of_another_size_is_refused(self) -> None:
        with pytest.raises(ValueError, match=str(PROGRAM_BLOCK_SIZE)):
            SHELL.with_program(self.block(SONG_ADDRESS)[:-1])

    def test_a_block_naming_another_song_address_is_refused(self) -> None:
        with pytest.raises(ValueError, match="another song address"):
            SHELL.with_program(self.block(SONG_ADDRESS + 1))
