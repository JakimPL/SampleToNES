from pydantic import BaseModel


class TreeNodeState(BaseModel):
    parent: str
    has_favorite_ancestor: bool = False
