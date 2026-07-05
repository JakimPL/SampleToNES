from pydantic import BaseModel, Field


class SampleRecord(BaseModel):
    """The on-disk form of a sample: its identity plus a reference to the
    reconstruction stored separately in the archive."""

    id: str = Field(..., description="Stable sample id.")
    name: str = Field(..., description="Sample name.")
    reconstruction_id: str = Field(
        ...,
        description="Id of the reconstruction stored in the archive.",
    )
