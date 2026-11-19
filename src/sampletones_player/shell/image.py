from __future__ import annotations

from importlib import resources
from typing import Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_core.formats.binary import BinaryReader
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.memory import NMI_VECTOR
from sampletones_player.specification.program import (
    LINKED_SONG_OFFSET,
    PROGRAM_BLOCK_SIZE,
)
from sampletones_player.specification.shell import (
    ADDRESS_SPACE_END,
    SHELL_BINARY_DIRECTORY,
    SHELL_CODE_NAME,
    SHELL_PACKAGE,
    VECTOR_COUNT,
    VECTORS_SIZE,
)


class ShellImage(BaseModel):
    """The assembled code that turns the driver into a cartridge: its start-up, its screen and its controls.

    The shell is built once by ``sampletones driver`` together with the driver it calls, and is
    committed beside it, so writing a cartridge needs no assembler. It ends at the top of the
    address space, where the console reads its vectors, and opens with the program block: the
    room the exporter fills with what the screen shows about the song.

    Attributes:
        code: The assembled bytes, from the program block to the vectors.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: bytes = Field(..., min_length=PROGRAM_BLOCK_SIZE + VECTORS_SIZE)

    @model_validator(mode="after")
    def _validate_the_vectors_lie_in_the_shell(self) -> ShellImage:
        for index, vector in enumerate(self.vectors):
            if not self.start + PROGRAM_BLOCK_SIZE <= vector < NMI_VECTOR:
                address = NMI_VECTOR + index * WORD_SIZE
                raise ValueError(
                    f"the vector at {address:#06x} points to {vector:#06x}, outside the shell's code between "
                    f"{self.start + PROGRAM_BLOCK_SIZE:#06x} and {NMI_VECTOR:#06x}"
                )

        return self

    @classmethod
    def load(cls) -> ShellImage:
        """Reads the shell committed in the package."""
        return cls(code=(resources.files(SHELL_PACKAGE) / SHELL_BINARY_DIRECTORY / SHELL_CODE_NAME).read_bytes())

    @property
    def start(self) -> int:
        """Where the shell is loaded, which puts its last bytes at the top of the address space."""
        return ADDRESS_SPACE_END - len(self.code)

    @property
    def linked_song(self) -> int:
        """Where the shell was built to find the song, which is behind the driver it was built with."""
        return self._word(LINKED_SONG_OFFSET)

    @property
    def vectors(self) -> Tuple[int, ...]:
        """The routines the console enters on a frame, on power-on and on an interrupt."""
        first = len(self.code) - VECTORS_SIZE
        return tuple(self._word(first + index * WORD_SIZE) for index in range(VECTOR_COUNT))

    def with_program(self, block: bytes) -> bytes:
        """The shell's bytes with its program block written.

        Args:
            block: What the screen shows about the song, laid out as the block states.

        Returns:
            bytes: The whole shell, its block replaced by ``block``.

        Raises:
            ValueError: If ``block`` takes another size than the block, or names another song
                address than the one the shell was built with.
        """
        if len(block) != PROGRAM_BLOCK_SIZE:
            raise ValueError(f"a program block takes {PROGRAM_BLOCK_SIZE} bytes, got {len(block)}")

        if block[LINKED_SONG_OFFSET : LINKED_SONG_OFFSET + WORD_SIZE] != self.code[:WORD_SIZE]:
            raise ValueError("the program block names another song address than the one the shell was built with")

        return block + self.code[PROGRAM_BLOCK_SIZE:]

    def _word(self, offset: int) -> int:
        return BinaryReader(self.code[offset : offset + WORD_SIZE]).read_uint16()
