from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import GeneratorName


class SubInstrument(BaseModel):
    """A reference to a single NES-channel slice of an instrument's reconstruction.

    A reconstruction may span up to four channels (two pulse, triangle, noise).
    A subinstrument pins one of those channels for use on a tracker row. The
    instrument is referenced by its stable ``id`` (never by collection position),
    so the reference survives reordering of the instruments collection.
    """

    model_config = ConfigDict(frozen=True)

    instrument_id: str = Field(..., description="Stable id of the referenced instrument.")
    generator_name: GeneratorName = Field(..., description="Which reconstruction channel-slice to use.")
