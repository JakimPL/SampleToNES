from pydantic import BaseModel, ConfigDict


class TableCell(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    value: str
