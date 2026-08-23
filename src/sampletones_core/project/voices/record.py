from typing import Literal, Optional

from pydantic import BaseModel, Field


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
    loop_point: Optional[int] = Field(
        default=None,
        ge=0,
        description="Tick the sample's instructions repeat from, or None where it plays once.",
    )
