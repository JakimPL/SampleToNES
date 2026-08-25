from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sampletones_player.specification.driver import (
    INIT_ADDRESS,
    LOAD_ADDRESS,
    MAX_ADDRESS,
    PLAY_ADDRESS,
)


class DriverAddresses(BaseModel):
    """Where the driver and the song it carries sit in the console's address space.

    Three of the four are settled before anything is assembled: the image loads at the start of
    the program area, and a jump table leads it so both routines answer at a fixed address
    whatever the driver's length. The song follows the code, so its address is the one value a
    build decides, and it decides it by the number of bytes it produced.

    Attributes:
        load: Where the console loads the image.
        init: The routine that readies the APU and sounds the song's first tick.
        play: The routine the console calls at the rate the NSF header asks for.
        song: Where the song block belongs, directly behind the code.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    load: int = Field(default=LOAD_ADDRESS, ge=0, le=MAX_ADDRESS)
    init: int = Field(default=INIT_ADDRESS, ge=0, le=MAX_ADDRESS)
    play: int = Field(default=PLAY_ADDRESS, ge=0, le=MAX_ADDRESS)
    song: int = Field(..., ge=0, le=MAX_ADDRESS)

    @classmethod
    def for_code(cls, code_length: int) -> DriverAddresses:
        """The addresses a driver of ``code_length`` bytes is built to answer at.

        A build holds its linker's own labels against these, and the exporter reads them without
        one, which is what keeps the committed image and the addresses that describe it in step.

        Args:
            code_length: The assembled driver's length in bytes.

        Returns:
            DriverAddresses: The addresses the image is expected to lay out.
        """
        return cls(song=LOAD_ADDRESS + code_length)
