from types import ModuleType

from pydantic import Field

from sampletones.constants.general import (
    DUTY_CYCLES,
    MAX_DUTY_CYCLE,
    MAX_PITCH,
    MAX_VOLUME,
    MIN_PITCH,
    PITCH_RANGE,
)
from sampletones.utils import pitch_to_name

from .instruction import Instruction


class PulseInstruction(Instruction):
    pitch: int = Field(..., ge=MIN_PITCH, le=MAX_PITCH, description="MIDI pitch (0-120)")
    volume: int = Field(..., ge=0, le=MAX_VOLUME, description="Volume (0-15)")
    duty_cycle: int = Field(..., ge=0, le=MAX_DUTY_CYCLE, description="Duty cycle (e.g. 12, 25, 50, 75)")

    @property
    def name(self) -> str:
        pitch = pitch_to_name(self.pitch)
        volume = f"v{self.volume:X}"
        duty = f"D{DUTY_CYCLES[self.duty_cycle]*100:.0f}"
        return f"P {pitch} {volume} {duty}"

    def __lt__(self, other: "PulseInstruction") -> bool:
        if not isinstance(other, PulseInstruction):
            return TypeError("Cannot compare PulseInstruction with different type")
        return (self.pitch, -self.volume, self.duty_cycle) < (other.pitch, -other.volume, other.duty_cycle)

    def distance(self, other: Instruction) -> float:
        if not isinstance(other, PulseInstruction):
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

        pitch1 = self.pitch
        pitch2 = other.pitch

        pitch_difference = abs(pitch1 - pitch2) / PITCH_RANGE

        if pitch_difference == 0:
            return abs(volume1_normalized - volume2_normalized) * 0.5

        volume_factor = (volume1_normalized + volume2_normalized) * 0.5
        pitch_distance = pitch_difference * volume_factor
        volume_distance = abs(volume1_normalized - volume2_normalized) * 0.25 * (1 - pitch_difference)

        return pitch_distance + volume_distance

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.instructions.pulse.PulseInstruction as FBPulseInstruction

        return FBPulseInstruction

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.instructions.pulse.PulseInstruction as FBPulseInstruction

        return FBPulseInstruction.PulseInstruction
