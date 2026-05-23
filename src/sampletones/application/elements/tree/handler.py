from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from sampletones.structures.tree import NodeType
from sampletones_shared.types.callback import Callback, MessageCallback


class NodeHandler(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    tag: str = Field(..., description="The unique tag for the handler registry.")
    node_type: NodeType = Field(..., description="The type of tree node this handler is for.")
    item_click_callback: Optional[Callback] = Field(
        default=None,
        description="Callback for item click events.",
    )
    item_double_click_callback: Optional[Callback] = Field(
        default=None,
        description="Callback for item double-click events.",
    )
    status_bar_callback: Optional[MessageCallback] = Field(
        default=None,
        description="Callback for updating the status bar with messages.",
    )
