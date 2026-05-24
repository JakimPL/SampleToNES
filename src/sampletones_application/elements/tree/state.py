from typing import Optional

from pydantic import BaseModel, ConfigDict

from sampletones_core.structures.tree import TreeNode


class TreeNodeState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    parent: str
    has_favorite_ancestor: bool = False
    special_node: Optional[TreeNode] = None
