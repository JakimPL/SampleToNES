from pydantic import BaseModel


class SourceSettingsLayout(BaseModel, extra="forbid", frozen=True):
    drive_format: str
    height: int
