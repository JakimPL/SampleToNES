from pydantic import Field

from sampletones.constants.general import MAX_PERIOD, MAX_VOLUME, NOISE_PERIODS

from .instruction import Instruction


class NoiseInstruction(Instruction):
    period: int = Field(..., ge=0, le=15, description="0-15, indexes into noise period table")
    volume: int = Field(..., ge=0, le=MAX_VOLUME, description="Volume (0-15)")
    short: bool = Field(..., description="False = normal (15-bit), True = short mode (93-step)")

    @property
    def name(self) -> str:
        period = f"p{NOISE_PERIODS[self.period]}"
        volume = f"v{self.volume:X}"
        short = "s" if self.short else "l"
        return f"N {period} {volume} {short}"

    def __lt__(self, other: "NoiseInstruction") -> bool:
        if not isinstance(other, NoiseInstruction):
            return TypeError("Cannot compare NoiseInstruction with different type")
        return (NOISE_PERIODS[self.period], -self.volume, self.short) < (
            NOISE_PERIODS[other.period],
            -other.volume,
            other.short,
        )

    def distance(self, other: Instruction) -> float:
        if not isinstance(other, NoiseInstruction):
            raise TypeError("Cannot compute distance between different instruction types")

        volume1 = self.volume if self.on else 0
        volume2 = other.volume if other.on else 0

        if volume1 == 0 and volume2 == 0:
            return 0.0

        volume1_normalized = volume1 / MAX_VOLUME
        volume2_normalized = volume2 / MAX_VOLUME

        if volume1 == 0:
            return volume2_normalized * 0.5

        if volume2 == 0:
            return volume1_normalized * 0.5

        period1 = self.period
        period2 = other.period
        period_differences = abs(period1 - period2) / MAX_PERIOD

        if period_differences == 0:
            return abs(volume1_normalized - volume2_normalized) * 0.5

        volume_factor = (volume1_normalized + volume2_normalized) * 0.5
        period_distance = period_differences * volume_factor
        volume_distance = abs(volume1_normalized - volume2_normalized) * 0.25 * (1 - period_differences)

        return period_distance + volume_distance
