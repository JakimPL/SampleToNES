from dataclasses import dataclass

from sampletones_core.structures.tree import TreeNode


@dataclass(frozen=True)
class NodeSpec:
    """A single tree widget resolved off the main thread, ready for emission.

    The background traversal computes every per-node value here — tags, labels,
    open/leaf flags, the selected theme and handler-registry tags — so the
    main-thread emitter only creates the widget and binds the pre-selected
    theme, font, and handler. ``node`` travels with the spec as the widget's
    user data, which the click and hover handlers read back.
    """

    node: TreeNode
    node_tag: str
    parent_tag: str
    label: str
    leaf: bool
    open_on_arrow: bool
    open_on_double_click: bool
    should_expand: bool
    theme_tag: str
    handler_tag: str
