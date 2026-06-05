from pydantic import BaseModel, Field


class InstrumentRecord(BaseModel):
    """The on-disk form of an instrument: its identity plus a reference to the
    reconstruction stored separately in the archive (never the binary itself)."""

    id: str = Field(..., description="Stable instrument id.")
    name: str = Field(..., description="Instrument name.")
    reconstruction_id: str = Field(..., description="Id of the reconstruction stored in the archive.")
