from pydantic import BaseModel


class AudioDevice(BaseModel):
    index: int
    name: str
    is_input: bool
    is_output: bool
    is_default_input: bool
    is_default_output: bool

    class Config:
        frozen = True
