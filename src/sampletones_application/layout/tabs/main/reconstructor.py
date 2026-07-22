from pydantic import BaseModel


class ReconstructorLayout(BaseModel, extra="forbid", frozen=True):
    drive_format: str
    height: int
