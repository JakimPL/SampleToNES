from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ConfigParameter(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str
    section: Literal["general", "library", "generation"]
    default: Any
