from typing import List, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from sampletones_core.constants.general import MAX_DUTY_CYCLE, MAX_PITCH, MAX_VOLUME, MIN_PITCH
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import NOTES_CONFIG_PATH

Volume = int
DutyCycle = int


class NotesConfig(BaseModel):
    """The single notes the channels play, laid on a grid: one held note per sound, then silence.

    Attributes:
        first_pitch: The lowest note of the pulse and triangle grid.
        last_pitch: The highest note the grid may reach.
        pitch_step: The semitones between neighboring notes of the grid.
        volumes: The volumes every pulse and noise note sounds at.
        duty_cycles: The duty cycles every pulse note sounds with.
        alternating_duty_cycles: Duty cycles one of which joins each pitch in turn, for timbres the
            ear hears alike.
        sounding_frames: How many frames each note holds.
        silent_frames: How many frames of silence follow it.
        listed_pitch_stride: Every how many grid pitches the page lists a tonal note at the loudest volume.
        listed_noise_period_stride: Every how many noise periods the page lists a noise note at the
            loudest volume.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    first_pitch: int = Field(ge=MIN_PITCH, le=MAX_PITCH)
    last_pitch: int = Field(ge=MIN_PITCH, le=MAX_PITCH)
    pitch_step: PositiveInt
    volumes: List[Volume] = Field(min_length=1)
    duty_cycles: List[DutyCycle]
    alternating_duty_cycles: List[DutyCycle]
    sounding_frames: PositiveInt
    silent_frames: NonNegativeInt
    listed_pitch_stride: PositiveInt
    listed_noise_period_stride: PositiveInt

    @model_validator(mode="after")
    def _validate_grid(self) -> Self:
        if self.last_pitch < self.first_pitch:
            raise ValueError("The grid's last pitch must be at least its first")
        if any(not 1 <= volume <= MAX_VOLUME for volume in self.volumes):
            raise ValueError(f"Every volume must lie between 1 and {MAX_VOLUME}")
        if any(not 0 <= duty <= MAX_DUTY_CYCLE for duty in [*self.duty_cycles, *self.alternating_duty_cycles]):
            raise ValueError(f"Every duty cycle must lie between 0 and {MAX_DUTY_CYCLE}")
        if not self.duty_cycles and not self.alternating_duty_cycles:
            raise ValueError("A pulse note needs a duty cycle to sound with")

        return self

    @property
    def pitches(self) -> List[int]:
        """The grid's notes, from the first up in steps."""
        return list(range(self.first_pitch, self.last_pitch + 1, self.pitch_step))

    @classmethod
    def load(cls) -> Self:
        """The grid the package ships."""
        return load_yaml_model(NOTES_CONFIG_PATH, cls)
