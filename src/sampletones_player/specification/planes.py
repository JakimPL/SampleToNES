from __future__ import annotations

from enum import StrEnum
from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import (
    MAX_DUTY_CYCLE,
    MAX_PERIOD,
    MAX_VOLUME,
)
from sampletones_player.specification.binary import MAX_BYTE_VALUE
from sampletones_player.specification.compression import PITCH_INDEX_MASK
from sampletones_player.specification.registers import (
    DUTY_CYCLE_SHIFT,
    NOISE_MODE_SHIFT,
    SUSTAINED_LEVEL,
)

SINGLE_TICK: Final[int] = 1
NO_BITS: Final[int] = 0
COUNT_STEP: Final[int] = 0x10
SILENT_PITCH_INDEX: Final[int] = PITCH_INDEX_MASK


class PlaneForm(BaseModel):
    """How a plane's byte divides between the value its register reads and a repeat count.

    A channel's register reads some of a byte's bits and ignores the rest: a pulse channel's
    volume is four bits under two the hardware wants set, and a noise period is four bits with
    three above it that say nothing. A plane writes its value in the bits that reach the register
    and counts the ticks that value repeats for in the ones left over, so a run costs one byte
    however long it rests.

    The division is a mask, which is what keeps the reading cheap: the register byte is the
    symbol masked and ored with the bits the hardware fixes, and one repeat is a subtraction of
    ``COUNT_STEP``. A plane whose values need every bit states a full ``value_mask``, carries no
    count, and reads byte for byte.

    Attributes:
        value_mask: The bits the value occupies.
        value_or: The bits the register fixes, which every value of the plane carries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value_mask: int = Field(..., ge=0, le=MAX_BYTE_VALUE)
    value_or: int = Field(..., ge=0, le=MAX_BYTE_VALUE)

    @model_validator(mode="after")
    def _validate_the_fixed_bits_lie_outside_the_value(self) -> PlaneForm:
        if self.value_or & self.value_mask:
            raise ValueError(
                f"the bits a register fixes lie outside the value's own, and {self.value_or:#04x} "
                f"meets {self.value_mask:#04x}"
            )

        return self

    @model_validator(mode="after")
    def _validate_a_count_steps_from_one_place(self) -> PlaneForm:
        if self.counts and self.count_mask & -self.count_mask != COUNT_STEP:
            raise ValueError(
                f"a repeat count steps from {COUNT_STEP:#04x}, and {self.count_mask:#04x} steps "
                f"from {self.count_mask & -self.count_mask:#04x}"
            )

        return self

    @model_validator(mode="after")
    def _validate_the_count_occupies_one_run_of_bits(self) -> PlaneForm:
        counted = self.count_mask // COUNT_STEP if self.counts else NO_BITS
        if counted & (counted + 1):
            raise ValueError(f"a repeat count occupies one run of bits, and {self.count_mask:#04x} breaks apart")

        return self

    @property
    def count_mask(self) -> int:
        """The bits a repeat count occupies."""
        return MAX_BYTE_VALUE ^ self.value_mask

    @property
    def counts(self) -> bool:
        """Whether the plane's byte has room to count a repeat."""
        return bool(self.count_mask)

    @property
    def repeats(self) -> int:
        """The ticks one symbol covers at most."""
        if not self.counts:
            return SINGLE_TICK

        return self.count_mask // COUNT_STEP + SINGLE_TICK

    def symbol(
        self,
        value: int,
        repeats: int,
    ) -> int:
        """The byte a plane writes for ``value`` sounding ``repeats`` ticks running.

        Args:
            value: The register byte the ticks play.
            repeats: The ticks the value sounds for.

        Returns:
            int: The symbol.

        Raises:
            ValueError: If the value carries fixed bits other than the form's, or the repeats
                reach past what one symbol counts.
        """
        if value & self.count_mask != self.value_or:
            raise ValueError(
                f"a value of this plane carries {self.value_or:#04x} in the bits the count takes, "
                f"and {value:#04x} carries {value & self.count_mask:#04x}"
            )

        if not SINGLE_TICK <= repeats <= self.repeats:
            raise ValueError(f"one symbol counts {SINGLE_TICK} through {self.repeats} ticks, and this counts {repeats}")

        return (value & self.value_mask) | (repeats - SINGLE_TICK) * COUNT_STEP

    def value(self, symbol: int) -> int:
        """The register byte ``symbol`` plays."""
        return (symbol & self.value_mask) | self.value_or

    def repeated(self, symbol: int) -> int:
        """The ticks ``symbol`` covers."""
        if not self.counts:
            return SINGLE_TICK

        return (symbol & self.count_mask) // COUNT_STEP + SINGLE_TICK

    def fits(self, plane: bytes) -> bool:
        """Whether every value the plane plays carries the bits this form fixes.

        Args:
            plane: The values the plane plays.

        Returns:
            bool: Whether the form reads the plane.
        """
        return all(value & self.count_mask == self.value_or for value in plane)


WHOLE_BYTE: Final[PlaneForm] = PlaneForm(value_mask=MAX_BYTE_VALUE, value_or=NO_BITS)

DUTY_CYCLE_FIELD: Final[int] = MAX_DUTY_CYCLE << DUTY_CYCLE_SHIFT
VOLUME_FIELD: Final[int] = MAX_VOLUME
PERIOD_FIELD: Final[int] = MAX_PERIOD
NOISE_MODE_FIELD: Final[int] = 1 << NOISE_MODE_SHIFT

PULSE_CONTROL_FORM: Final[PlaneForm] = PlaneForm(
    value_mask=DUTY_CYCLE_FIELD | VOLUME_FIELD,
    value_or=SUSTAINED_LEVEL,
)
NOISE_CONTROL_FORM: Final[PlaneForm] = PlaneForm(
    value_mask=VOLUME_FIELD,
    value_or=SUSTAINED_LEVEL,
)
NOISE_VALUE_FORM: Final[PlaneForm] = PlaneForm(
    value_mask=NOISE_MODE_FIELD | PERIOD_FIELD,
    value_or=NO_BITS,
)


class PlaneRole(StrEnum):
    """The part of a channel's tick one plane carries.

    Attributes:
        CONTROL: How the channel sounds — its timbre, and its volume where it has one.
        VALUE: What the channel sounds — a pitch index, or the noise channel's period byte.
        BEND: How far a tick stands from the divider the pitch it names sounds at.
    """

    CONTROL = "control"
    VALUE = "value"
    BEND = "bend"


class Plane(BaseModel):
    """One byte series a song block writes, named by the channel and the part it carries.

    Attributes:
        channel: The channel the plane belongs to.
        role: The part of the channel's tick the plane carries.
        form: How the plane's byte divides between its value and a repeat count.
        seeded: The register byte the plane stands at before its first token, which the driver
            writes when it starts a song and a plane holding it throughout takes no stream.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: ChannelName
    role: PlaneRole
    form: PlaneForm
    seeded: int = Field(..., ge=0, le=MAX_BYTE_VALUE)

    @model_validator(mode="after")
    def _validate_the_seeded_value_reads_as_the_plane_does(self) -> Plane:
        if not self.form.fits(bytes((self.seeded,))):
            raise ValueError(
                f"a plane stands at a value its own form reads, and {self.name} stands at {self.seeded:#04x}"
            )

        return self

    @property
    def name(self) -> str:
        """The name the song block writes the plane under."""
        return f"{self.channel.value}_{self.role.value}"

    @property
    def spans_flagged_ticks(self) -> bool:
        """Whether the plane holds a value per flagged tick rather than one per tick."""
        return self.role is PlaneRole.BEND

    def idles(self, played: bytes) -> bool:
        """Whether the plane holds the value it is seeded to throughout, so it takes no stream.

        Args:
            played: The values the plane plays.

        Returns:
            bool: Whether the plane stands where the driver seeds it.
        """
        return set(played) <= {self.seeded}


def _tone(
    channel: ChannelName,
    role: PlaneRole,
) -> Plane:
    return Plane(channel=channel, role=role, form=WHOLE_BYTE, seeded=NO_BITS)


PLANES: Final[Tuple[Plane, ...]] = (
    Plane(
        channel=ChannelName.PULSE1,
        role=PlaneRole.CONTROL,
        form=PULSE_CONTROL_FORM,
        seeded=SUSTAINED_LEVEL,
    ),
    _tone(ChannelName.PULSE1, PlaneRole.VALUE),
    _tone(ChannelName.PULSE1, PlaneRole.BEND),
    Plane(
        channel=ChannelName.PULSE2,
        role=PlaneRole.CONTROL,
        form=PULSE_CONTROL_FORM,
        seeded=SUSTAINED_LEVEL,
    ),
    _tone(ChannelName.PULSE2, PlaneRole.VALUE),
    _tone(ChannelName.PULSE2, PlaneRole.BEND),
    Plane(
        channel=ChannelName.TRIANGLE,
        role=PlaneRole.VALUE,
        form=WHOLE_BYTE,
        seeded=SILENT_PITCH_INDEX,
    ),
    _tone(ChannelName.TRIANGLE, PlaneRole.BEND),
    Plane(
        channel=ChannelName.NOISE,
        role=PlaneRole.CONTROL,
        form=NOISE_CONTROL_FORM,
        seeded=SUSTAINED_LEVEL,
    ),
    Plane(
        channel=ChannelName.NOISE,
        role=PlaneRole.VALUE,
        form=NOISE_VALUE_FORM,
        seeded=NO_BITS,
    ),
)
PLANE_COUNT: Final[int] = len(PLANES)
PLANE_NAMES: Final[Tuple[str, ...]] = tuple(plane.name for plane in PLANES)


def channel_indices(channel: ChannelName) -> Tuple[int, ...]:
    """Where ``channel``'s own planes stand in the song block, in the order it writes them.

    Args:
        channel: The channel to read.

    Returns:
        Tuple[int, ...]: The positions that channel's planes take.
    """
    return tuple(index for index, plane in enumerate(PLANES) if plane.channel is channel)


def plane_index(
    channel: ChannelName,
    role: PlaneRole,
) -> int:
    """Where the plane ``channel`` writes for ``role`` stands in the song block.

    Args:
        channel: The channel the plane belongs to.
        role: The part of the channel's tick the plane carries.

    Returns:
        int: The position the plane takes.

    Raises:
        ValueError: If the channel writes no plane for that role.
    """
    for index, plane in enumerate(PLANES):
        if plane.channel is channel and plane.role is role:
            return index

    raise ValueError(f"the {channel.value} channel writes no {role.value} plane")
