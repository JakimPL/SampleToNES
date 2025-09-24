from pydantic import BaseModel


class Instruction(BaseModel):
    on: bool

    class Config:
        frozen = True
