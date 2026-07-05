from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import GeneratorName


class Instrument(BaseModel):
    """A reference to a single NES-channel slice of a sample's reconstruction.

    A reconstruction may span up to four channels (two pulse, triangle, noise).
    A subinstrument pins one of those channels for use on a tracker row. The
    sample is referenced by its stable ``id``, so the reference survives
    reordering of the samples collection.
    """

    model_config = ConfigDict(frozen=True)

    sample_id: str = Field(..., description="Stable id of the referenced sample.")
    generator_name: GeneratorName = Field(
        ...,
        description="Which reconstruction channel-slice to use.",
    )
