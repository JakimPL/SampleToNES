from pydantic import BaseModel


class OrderLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    position_column_width: int
    master_divider_height: int
