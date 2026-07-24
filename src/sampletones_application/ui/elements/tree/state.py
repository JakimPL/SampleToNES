from pydantic import BaseModel, ConfigDict


class TreeNodeState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    parent: str
    has_favorite_ancestor: bool = False
