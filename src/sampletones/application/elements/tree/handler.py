from typing import Any, Callable, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones.tree import TreeNode
from sampletones.typehints import MessageCallback, Sender

ItemClickCallback = Callable[[Sender, Tuple[int, int], Any], None]


class Handler(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    tag: str = Field(..., description="The unique tag for the handler registry.")
    parent: str = Field(..., description="The parent tag to which the handler registry is attached.")
    node: TreeNode = Field(..., description="The tree node associated with this handler.")
    item_click_callback: Optional[ItemClickCallback] = Field(
        default=None,
        description="Callback for item click events.",
    )
    item_double_click_callback: Optional[ItemClickCallback] = Field(
        default=None,
        description="Callback for item double-click events.",
    )
    status_bar_callback: Optional[MessageCallback] = Field(
        default=None,
        description="Callback for updating the status bar with messages.",
    )
