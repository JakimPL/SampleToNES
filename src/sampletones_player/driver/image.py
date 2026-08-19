from __future__ import annotations

from importlib import resources

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_player.driver.addresses import DriverAddresses
from sampletones_player.specification.driver import (
    DRIVER_CODE_NAME,
    DRIVER_PACKAGE,
    JUMP_ABSOLUTE_OPCODE,
)


class DriverImage(BaseModel):
    """The assembled player, paired with the addresses it lays out.

    The 6502 program that plays a song is written in assembly, built once by ``make player`` and
    committed beside its sources, so exporting an NSF needs no assembler. Pairing the bytes with
    their addresses is what lets the exporter name the routines in an NSF header and place the
    song where the driver looks for it.

    Attributes:
        code: The assembled bytes, loaded at the image's load address.
        addresses: Where the code and the song behind it sit.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: bytes = Field(..., min_length=1)
    addresses: DriverAddresses

    @model_validator(mode="after")
    def _validate_the_song_follows_the_code(self) -> DriverImage:
        expected = self.addresses.load + len(self.code)
        if self.addresses.song != expected:
            raise ValueError(
                f"the song belongs at {expected:#06x}, directly behind {len(self.code)} bytes of "
                f"code loaded at {self.addresses.load:#06x}, and the image states "
                f"{self.addresses.song:#06x}"
            )

        return self

    @model_validator(mode="after")
    def _validate_the_routines_lie_in_the_code(self) -> DriverImage:
        for name, address in (("init", self.addresses.init), ("play", self.addresses.play)):
            if not self.addresses.load <= address < self.addresses.song:
                raise ValueError(
                    f"the {name} routine lies at {address:#06x}, outside the code between "
                    f"{self.addresses.load:#06x} and {self.addresses.song:#06x}"
                )

        return self

    @model_validator(mode="after")
    def _validate_the_image_leads_with_its_entry_points(self) -> DriverImage:
        for name, address in (("init", self.addresses.init), ("play", self.addresses.play)):
            opcode = self.code[address - self.addresses.load]
            if opcode != JUMP_ABSOLUTE_OPCODE:
                raise ValueError(
                    f"the {name} routine answers at {address:#06x}, where the image holds "
                    f"{opcode:#04x} rather than the jump the entry points lead with"
                )

        return self

    @classmethod
    def load(cls) -> DriverImage:
        """Reads the driver committed in the package.

        Returns:
            DriverImage: The assembled bytes and the addresses they lay out.

        Raises:
            ValueError: If the committed bytes lay out something other than the addresses the
                driver is built to answer at.
        """
        code = (resources.files(DRIVER_PACKAGE) / DRIVER_CODE_NAME).read_bytes()
        return cls(code=code, addresses=DriverAddresses.for_code(len(code)))
