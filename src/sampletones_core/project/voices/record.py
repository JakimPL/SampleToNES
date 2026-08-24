from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from sampletones_core.project.voices.instrument import Instrument


class SampleRecord(BaseModel):
    """The on-disk form of a sample: its identity plus a reference to the
    reconstruction stored separately in the archive."""

    kind: Literal["sample"] = Field(default="sample", description="Which kind of voice this record carries.")
    id: str = Field(..., description="Stable sample id.")
    name: str = Field(..., description="Sample name.")
    reconstruction_id: str = Field(
        ...,
        description="Id of the reconstruction stored in the archive.",
    )


VoiceRecord = Annotated[Union[SampleRecord, Instrument], Field(discriminator="kind")]
"""The on-disk form of one voice, told apart by its ``kind``.

A sample is written as a reference to the reconstruction stored beside the document, while an instrument
carries only what it states and is written whole.
"""
