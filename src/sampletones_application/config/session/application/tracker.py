from pydantic import BaseModel, Field

from sampletones_application.constants.tracker import DEFAULT_OCTAVE, MAX_OCTAVE, MIN_OCTAVE


class TrackerConfig(BaseModel):
    octave: int = Field(
        default=DEFAULT_OCTAVE,
        ge=MIN_OCTAVE,
        le=MAX_OCTAVE,
        description="The octave a note key types into the pattern grid.",
    )
