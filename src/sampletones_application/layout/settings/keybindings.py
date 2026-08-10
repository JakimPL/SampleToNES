from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class KeybindingsSettingsLayout(BaseModel, extra="forbid", frozen=True):
    """The geometry the keybindings dialog draws with.

    The list takes a stated height so the window keeps one size whichever scope a filter leaves
    showing, and the action column takes a stated width so every combination reads down one edge.
    """

    window: Dimensions
    list_height: int
    action_width: int
