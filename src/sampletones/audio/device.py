from pydantic import BaseModel, ConfigDict


class AudioDevice(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    name: str
    is_input: bool
    is_output: bool
    is_default_input: bool
    is_default_output: bool
