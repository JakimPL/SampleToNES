from pydantic import BaseModel


class ConfigLayout(BaseModel, extra="forbid", frozen=True):
    height: int
